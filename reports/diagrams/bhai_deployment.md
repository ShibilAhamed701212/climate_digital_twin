# Deployment Architecture

```mermaid
graph TB
    subgraph Host[Host Machine]
        subgraph Docker[Docker Engine]
            subgraph Container[Benchmark Container]
                AppDir[/app]
                AppDir --> ProjectFiles[Project Files<br/>runtime/, climate/,<br/>pyproject.toml]
                AppDir --> ReportsDir[/reports]

                AppDir --> CMD[CMD: pytest runtime/benchmarks/]

                CMD --> TestOutput[Test Results]
                TestOutput --> ReportsDir
            end
        end

        HostDir[Host: ./reports]
        ComposeFile[docker-compose.benchmark.yml]
    end

    ReportsDir -->|volume mount| HostDir
    ComposeFile -->|docker compose up| Docker

    style Host fill:#f9f,stroke:#333
    style Docker fill:#9cf,stroke:#333
    style Container fill:#dfd,stroke:#333
    style HostDir fill:#ff9,stroke:#333
    style ComposeFile fill:#ddd,stroke:#333
```
