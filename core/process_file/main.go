package main

import (
	"context"
	"crypto/sha256"
	"fmt"
	"io"
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
    UserID    string    `json:"userId"`
    Date      time.Time `json:"date"`
    Amount    float64   `json:"amount"`
    Processed string    `json:"processed"`
}

// Genera un ID único usando los datos de la transacción
func generateUniqueID( userID, date string, amount float64, lineNumber int) string {
    // Combina todos los datos incluyendo el número de línea para asegurar unicidad
    data := fmt.Sprintf("%s-%s-%s-%.2f-%d", userID, date, amount, lineNumber)
    // Genera un hash de los datos
    hash := sha256.Sum256([]byte(data))
    // Retorna los primeros 16 caracteres del hash en hexadecimal
    return fmt.Sprintf("%x", hash)[:16]
}

func handleRequest(ctx context.Context, s3Event events.S3Event) error {
    log.Printf("🚀 Lambda function started. Number of records to process: %d", len(s3Event.Records))
    
    cfg, err := config.LoadDefaultConfig(ctx)
    if err != nil {
        log.Printf("❌ ERROR: Failed to load SDK config: %v", err)
        return fmt.Errorf("unable to load SDK config: %v", err)
    }

    s3Client := s3.NewFromConfig(cfg)
    dynamoClient := dynamodb.NewFromConfig(cfg)

    for i, record := range s3Event.Records {
        log.Printf("📁 Processing S3 record %d of %d", i+1, len(s3Event.Records))
        
        bucket := record.S3.Bucket.Name
        key := record.S3.Object.Key

        result, err := s3Client.GetObject(ctx, &s3.GetObjectInput{
            Bucket: &bucket,
            Key:    &key,
        })
        if err != nil {
            log.Printf("❌ ERROR: Failed to get object from S3: %v", err)
            continue
        }

        content, err := io.ReadAll(result.Body)
        result.Body.Close()

        if err != nil {
            log.Printf("❌ ERROR: Failed to read file contents: %v", err)
            continue
        }

        lines := strings.Split(string(content), "\n")
        log.Printf("📊 Total number of lines found: %d", len(lines))

        lineCount := 0
        successCount := 0
        errorCount := 0

        for _, line := range lines {
            lineCount++
            line = strings.TrimSpace(line)
            
            if line == "" {
                continue
            }

            log.Printf("📝 Processing line %d: %s", lineCount, line)

            parts := strings.Split(line, ",")
            for i := range parts {
                parts[i] = strings.TrimSpace(parts[i])
            }

            if len(parts) != 3 {
                log.Printf("❌ ERROR: Invalid line format at line %d: expected 3 parts, got %d", lineCount, len(parts))
                errorCount++
                continue
            }

            date, err := time.Parse("2006-01-02", parts[1])
            if err != nil {
                log.Printf("❌ ERROR: Failed to parse date at line %d: %v", lineCount, err)
                errorCount++
                continue
            }

            amount, err := strconv.ParseFloat(parts[2], 64)
            if err != nil {
                log.Printf("❌ ERROR: Failed to parse amount at line %d: %v", lineCount, err)
                errorCount++
                continue
            }

            // Generar un ID único para cada transacción
            uniqueID := generateUniqueID(parts[1], parts[2], amount, lineCount)

            log.Printf("🔑 Generated unique ID for line %d: %s", lineCount, uniqueID)

            transaction := Transaction{
                ID:        uniqueID, // Usar el ID único generado
                UserID:    parts[0],
                Date:      date,
                Amount:    amount,
                Processed: "Ok",
            }

            tableName := "movements"
            log.Printf("💾 Saving transaction with ID: %s", uniqueID)

            _, err = dynamoClient.PutItem(ctx, &dynamodb.PutItemInput{
                TableName: &tableName,
                Item: map[string]types.AttributeValue{
                    "id":        &types.AttributeValueMemberS{Value: transaction.ID},
                    "UserId":    &types.AttributeValueMemberS{Value: transaction.UserID},
                    "Date":      &types.AttributeValueMemberS{Value: transaction.Date.Format("2006-01-02")},
                    "amount":    &types.AttributeValueMemberN{Value: fmt.Sprintf("%.2f", transaction.Amount)},
                    "processed": &types.AttributeValueMemberS{Value: transaction.Processed},
                },
            })
            if err != nil {
                log.Printf("❌ ERROR: Failed to save transaction %s to DynamoDB: %v", uniqueID, err)
                errorCount++
                continue
            }

            successCount++
            log.Printf("✅ Successfully saved transaction - ID: %s", uniqueID)
        }

        log.Printf("🏁 File processing completed!")
        log.Printf("📊 Final Statistics:")
        log.Printf("   - Total Lines Processed: %d", lineCount)
        log.Printf("   - Successful Transactions: %d", successCount)
        log.Printf("   - Errors: %d", errorCount)
    }

    return nil
}

func main() {
    lambda.Start(handleRequest)
}