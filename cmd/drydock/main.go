package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/signal"

	"drydock/internal/sandbox"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()
	os.Exit(run(ctx, os.Args[1:], os.Stdout, os.Stderr))
}

func run(ctx context.Context, args []string, stdout, stderr io.Writer) int {
	if len(args) != 1 || args[0] != "preflight" {
		fmt.Fprintln(stderr, "usage: drydock preflight")
		return 2
	}
	r := sandbox.Preflight(ctx)
	if err := json.NewEncoder(stdout).Encode(r); err != nil {
		fmt.Fprintln(stderr, "could not write preflight report")
		return 1
	}
	if !r.Qualified {
		fmt.Fprintln(stderr, "execution unavailable: "+r.BlockingChecks())
		return 1
	}
	return 0
}
