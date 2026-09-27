package sandbox

import (
	"context"
	"errors"
	"testing"
)

func TestUnsupportedHostDoesNotQueryDocker(t *testing.T) {
	r := preflight(context.Background(), "darwin", "arm64", func(context.Context) ([]byte, error) {
		t.Fatal("unsupported host must not query Docker")
		return nil, nil
	})
	if r.Qualified || r.BlockingChecks() != "linux_host" {
		t.Fatalf("unexpected report: %+v", r)
	}
}

func TestMetadataNeverQualifiesRuntime(t *testing.T) {
	cases := []struct {
		name, metadata, blocked string
		err                     error
	}{
		{"missing", "", "docker_info", errors.New("unavailable")},
		{"malformed", "{", "docker_info", nil},
		{"empty", "{}", "linux_engine, rootless_engine, isolation_probes", nil},
		{"rootful", `{"OSType":"linux","SecurityOptions":["name=seccomp"]}`, "rootless_engine, isolation_probes", nil},
		{"rootless", `{"OSType":"linux","SecurityOptions":["name=rootless"]}`, "isolation_probes", nil},
		{"lookalike", `{"OSType":"linux","SecurityOptions":["name=rootless-disabled"]}`, "rootless_engine, isolation_probes", nil},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			r := preflight(context.Background(), "linux", "amd64", func(context.Context) ([]byte, error) {
				return []byte(tc.metadata), tc.err
			})
			if r.Qualified || r.BlockingChecks() != tc.blocked {
				t.Fatalf("unexpected report: %+v", r)
			}
		})
	}
}

func TestMetadataOutputBound(t *testing.T) {
	b := &limitedBuffer{remaining: 3}
	if _, err := b.Write([]byte("abc")); err != nil {
		t.Fatal(err)
	}
	if _, err := b.Write([]byte("d")); err == nil || b.String() != "abc" {
		t.Fatal("output bound not enforced")
	}
}
