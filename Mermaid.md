graph TD
    subgraph "User Layer"
        User[QA / Developer] -->|Natural Language Prompt| Copilot[GitHub Copilot Agent]
    end

    subgraph "The Intelligence Bridge (MCP)"
        Copilot <-->|Handshake| MCP[MCP Server: Python/Java]
        MCP <-->|Live Scan| Codebase[(Existing Java Steps & Data Templates)]
    end

    subgraph "Output Generation"
        Copilot -->|1. Accurate Syntax| BDD[.feature File]
        Copilot -->|2. Valid Schema| Data[@dataFile / CSV]
        Copilot -->|3. Correct Logic| SQL[Validation Queries]
    end

    style MCP fill:#f96,stroke:#333,stroke-width:4px
    style Codebase fill:#bbf,stroke:#333

stateDiagram-v2
    [*] --> Requirement: "New Batch Job X"
    Requirement --> MCP_Scan: AI consults MCP Server
    
    state MCP_Scan {
        direction LR
        Read_Java --> Map_Steps
        Read_CSV_Template --> Align_Headers
    }

    MCP_Scan --> Draft_BDD: AI Generates Feature + Data Row
    Draft_BDD --> Human_Review: One-click approval
    Human_Review --> Save: File saved to Repo
    Save --> [*]: Ready for TestNG Execution
