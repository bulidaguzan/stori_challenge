package main

import (
	"bufio"
	"context"
	"fmt"
	"log"
	"strconv"
	"strings"
	"time"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

type Transaction struct {
    ID        string    `json:"id"`
    Date      time.Time `json:"date"`
    Amount    float64   `json:"amount"`
    Processed string    `json:"processed"`
}

func handleRequest(ctx context.Context, s3Event events.S3Event) error {
    log.Printf("Lambda function started. Number of records to process: %d", len(s3Event.Records))
    
    // Configurar clientes AWS
    log.Println("Loading AWS SDK configuration...")
    cfg, err := config.LoadDefaultConfig(ctx)
    if err != nil {
        log.Printf("ERROR: Failed to load SDK config: %v", err)
        return fmt.Errorf("unable to load SDK config: %v", err)
    }
    log.Println("AWS SDK configuration loaded successfully")

    log.Println("Initializing S3 and DynamoDB clients...")
    s3Client := s3.NewFromConfig(cfg)
    dynamoClient := dynamodb.NewFromConfig(cfg)
    log.Println("AWS clients initialized successfully")

    // Procesar cada registro del evento S3
    for i, record := range s3Event.Records {
        log.Printf("Processing record %d of %d", i+1, len(s3Event.Records))
        log.Printf("Processing file from bucket: %s, key: %s", record.S3.Bucket.Name, record.S3.Object.Key)
        
        bucket := record.S3.Bucket.Name
        key := record.S3.Object.Key

        // Obtener el archivo de S3
        log.Printf("Attempting to get object from S3: %s/%s", bucket, key)
        result, err := s3Client.GetObject(ctx, &s3.GetObjectInput{
            Bucket: &bucket,
            Key:    &key,
        })
        if err != nil {
            log.Printf("ERROR: Failed to get object from S3: %v", err)
            return fmt.Errorf("error getting object %s/%s: %v", bucket, key, err)
        }
        log.Println("Successfully retrieved object from S3")

        // Leer el archivo línea por línea
        log.Println("Starting to scan file contents...")
        scanner := bufio.NewScanner(result.Body)
        lineCount := 0
        successCount := 0
        errorCount := 0

        for scanner.Scan() {
            lineCount++
            line := scanner.Text()
            log.Printf("Processing line %d: %s", lineCount, line)
            
            // Parsear la línea
            parts := strings.Split(line, ",")
            if len(parts) != 3 {
                log.Printf("ERROR: Invalid line format at line %d: %s (expected 3 parts, got %d)", lineCount, line, len(parts))
                errorCount++
                continue
            }
            log.Printf("Line %d split successfully into %d parts", lineCount, len(parts))

            // Crear estructura de transacción
            log.Printf("Parsing amount from string: %s", parts[2])
            amount, err := strconv.ParseFloat(parts[2], 64)
            if err != nil {
                log.Printf("ERROR: Failed to parse amount at line %d: %v", lineCount, err)
                errorCount++
                continue
            }
            log.Printf("Amount parsed successfully: %f", amount)

            log.Printf("Parsing date from string: %s", parts[1])
            date, err := time.Parse("2006-01-02", parts[1])
            if err != nil {
                log.Printf("ERROR: Failed to parse date at line %d: %v", lineCount, err)
                errorCount++
                continue
            }
            log.Printf("Date parsed successfully: %v", date)

            transaction := Transaction{
                ID:        parts[0],
                Date:      date,
                Amount:    amount,
                Processed: "Ok",
            }
            log.Printf("Created transaction object: %+v", transaction)

            tableName := "movements"
            log.Printf("Attempting to save transaction %s to DynamoDB table %s", transaction.ID, tableName)
            
            // Guardar en DynamoDB
            _, err = dynamoClient.PutItem(ctx, &dynamodb.PutItemInput{
                TableName: &tableName,
                Item: map[string]types.AttributeValue{
                    "id":        &types.AttributeValueMemberS{Value: transaction.ID},
                    "date":      &types.AttributeValueMemberS{Value: transaction.Date.Format("2006-01-02")},
                    "amount":    &types.AttributeValueMemberN{Value: fmt.Sprintf("%f", transaction.Amount)},
                    "processed": &types.AttributeValueMemberS{Value: transaction.Processed},
                },
            })
            if err != nil {
                log.Printf("ERROR: Failed to save transaction %s to DynamoDB: %v", transaction.ID, err)
                errorCount++
                continue
            }

            log.Printf("Successfully saved transaction %s to DynamoDB", transaction.ID)
            successCount++
            log.Printf("Current processing stats - Success: %d, Errors: %d, Total Processed: %d", 
                      successCount, errorCount, lineCount)
        }

        if err := scanner.Err(); err != nil {
            log.Printf("ERROR: Failed to read file completely: %v", err)
            return fmt.Errorf("error reading file: %v", err)
        }

        log.Printf("File processing completed. Final stats - Total Lines: %d, Success: %d, Errors: %d", 
                  lineCount, successCount, errorCount)
    }

    log.Println("Lambda function completed successfully")
    return nil
}

func main() {
    log.Println("Lambda function initializing...")
    lambda.Start(handleRequest)
}