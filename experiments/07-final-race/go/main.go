package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"

	"github.com/aws/aws-lambda-go/lambda"
)

type Event struct {
	Message    string `json:"message"`
	Iterations int    `json:"iterations"`
}

type Response struct {
	StatusCode int    `json:"statusCode"`
	Body       string `json:"body"`
}

func handler(ctx context.Context, event Event) (Response, error) {
	message := event.Message
	if message == "" {
		message = "LazyTown"
	}
	iterations := event.Iterations
	if iterations == 0 {
		iterations = 20000
	}

	value := []byte(message)
	for i := 0; i < iterations; i++ {
		sum := sha256.Sum256(value)
		value = sum[:]
	}

	bodyBytes, err := json.Marshal(map[string]any{
		"hash":       hex.EncodeToString(value),
		"iterations": iterations,
	})
	if err != nil {
		return Response{}, err
	}

	return Response{
		StatusCode: 200,
		Body:       string(bodyBytes),
	}, nil
}

func main() {
	lambda.Start(handler)
}
