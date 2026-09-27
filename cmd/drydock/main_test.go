package main

import (
	"bytes"
	"context"
	"encoding/json"
	"testing"

	"drydock/internal/sandbox"
)

func TestPreflightFailsClosed(t *testing.T) {
	var out, errout bytes.Buffer
	if code := run(context.Background(), []string{"preflight"}, &out, &errout); code != 1 {
		t.Fatalf("exit code %d; expected unqualified", code)
	}
	var report sandbox.Report
	if err := json.Unmarshal(out.Bytes(), &report); err != nil {
		t.Fatal(err)
	}
	if report.Qualified || report.SchemaVersion != "1" || errout.Len() == 0 {
		t.Fatalf("unexpected report: %+v", report)
	}
}

func TestUnsupportedCommand(t *testing.T) {
	var out, errout bytes.Buffer
	if code := run(context.Background(), []string{"serve"}, &out, &errout); code != 2 || out.Len() != 0 {
		t.Fatal("unimplemented command must fail")
	}
}
