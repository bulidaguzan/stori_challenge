FROM golang:1.21-alpine AS builder

WORKDIR /build
COPY . .

# Initialize module and obtain dependencies
RUN go mod init lambda-go && \
    go get github.com/aws/aws-lambda-go/lambda && \
    go get github.com/aws/aws-lambda-go/events && \
    go mod tidy

# Compile the application
RUN CGO_ENABLED=0 GOOS=linux go build -o bootstrap

# Final image
FROM public.ecr.aws/lambda/provided:al2

# Copy the compiled binary
COPY --from=builder /build/bootstrap /var/runtime/bootstrap
# Make the binary executable
RUN chmod +x /var/runtime/bootstrap
# Configure the handler
ENTRYPOINT [ "/var/runtime/bootstrap" ]



