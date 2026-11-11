package main

import (
	"context"
	"encoding/json"

	"github.com/aws/aws-lambda-go/lambda"
)

type Row struct {
	Value int `json:"value"`
}

type Event struct {
	Type string `json:"type"`
	Rows []Row  `json:"rows"`
}

type Response struct {
	StatusCode int    `json:"statusCode"`
	Body       string `json:"body"`
}

func handler(ctx context.Context, event Event) (Response, error) {
	var body any = map[string]any{"mode": "simple", "ok": true}
	if event.Type == "report" {
		total := 0
		for _, r := range event.Rows {
			total += r.Value
		}
		body = map[string]any{"mode": "report", "total": total}
	}
	b, err := json.Marshal(body)
	if err != nil {
		return Response{}, err
	}
	return Response{StatusCode: 200, Body: string(b)}, nil
}

func main() {
	lambda.Start(handler)
}
