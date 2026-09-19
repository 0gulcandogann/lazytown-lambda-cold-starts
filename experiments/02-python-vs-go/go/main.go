package main

import (
	"context"

	"github.com/aws/aws-lambda-go/lambda"
)

type Response struct {
	StatusCode int               `json:"statusCode"`
	Body       string            `json:"body"`
	Headers    map[string]string `json:"headers,omitempty"`
}

func handler(ctx context.Context) (Response, error) {
	return Response{
		StatusCode: 200,
		Body:       `{"hello":"world"}`,
	}, nil
}

func main() {
	lambda.Start(handler)
}
