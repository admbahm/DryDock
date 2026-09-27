// Package sandbox owns execution-runtime qualification and, eventually,
// bounded job execution. A prerequisite check is not isolation qualification.
package sandbox

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os/exec"
	"runtime"
	"strings"
	"time"
)

type Check struct {
	Name   string `json:"name"`
	Passed bool   `json:"passed"`
	Detail string `json:"detail"`
}

type Report struct {
	SchemaVersion string  `json:"schema_version"`
	OS            string  `json:"os"`
	Architecture  string  `json:"architecture"`
	Checks        []Check `json:"checks"`
	Qualified     bool    `json:"qualified"`
}

// Preflight inspects prerequisites without creating containers, pulling images,
// or granting execution permission. Qualified remains false until behavioral
// isolation probes are implemented and demonstrated on the selected host.
func Preflight(ctx context.Context) Report {
	return preflight(ctx, runtime.GOOS, runtime.GOARCH, dockerInfo)
}

func preflight(ctx context.Context, hostOS, arch string, info func(context.Context) ([]byte, error)) Report {
	r := Report{SchemaVersion: "1", OS: hostOS, Architecture: arch, Checks: []Check{}}
	r.Checks = append(r.Checks, Check{"linux_host", hostOS == "linux", "supported execution OS is linux"})
	if hostOS != "linux" {
		return r
	}
	data, err := info(ctx)
	if err != nil {
		r.Checks = append(r.Checks, Check{"docker_info", false, err.Error()})
		return r
	}
	var engine struct {
		OSType          string
		SecurityOptions []string
	}
	if err := json.Unmarshal(data, &engine); err != nil {
		r.Checks = append(r.Checks, Check{"docker_info", false, "invalid Docker metadata"})
		return r
	}
	r.Checks = append(r.Checks, Check{"linux_engine", engine.OSType == "linux", "Docker engine must report linux"})
	rootless := false
	for _, option := range engine.SecurityOptions {
		if option == "name=rootless" {
			rootless = true
		}
	}
	r.Checks = append(r.Checks, Check{"rootless_engine", rootless, "Docker metadata must report name=rootless"})
	r.Checks = append(r.Checks, Check{"isolation_probes", false, "not implemented or demonstrated; execution is unavailable"})
	return r
}

func dockerInfo(ctx context.Context) ([]byte, error) {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "docker", "info", "--format", "{{json .}}")
	cmd.WaitDelay = time.Second
	out := &limitedBuffer{remaining: 64 * 1024}
	cmd.Stdout = out
	// Do not include daemon diagnostics, which may contain operator configuration.
	if err := cmd.Run(); err != nil {
		if ctx.Err() != nil {
			return nil, fmt.Errorf("Docker metadata query interrupted: %w", ctx.Err())
		}
		if errors.Is(err, exec.ErrNotFound) {
			return nil, errors.New("Docker executable unavailable")
		}
		return nil, errors.New("Docker metadata query failed")
	}
	return out.Bytes(), nil
}

type limitedBuffer struct {
	bytes.Buffer
	remaining int
}

func (b *limitedBuffer) Write(p []byte) (int, error) {
	if len(p) > b.remaining {
		return 0, errors.New("Docker metadata exceeds output limit")
	}
	b.remaining -= len(p)
	return b.Buffer.Write(p)
}

// BlockingChecks returns stable identifiers suitable for CLI diagnostics.
func (r Report) BlockingChecks() string {
	var names []string
	for _, c := range r.Checks {
		if !c.Passed {
			names = append(names, c.Name)
		}
	}
	return strings.Join(names, ", ")
}
