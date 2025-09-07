# FinLite AI Excel Add-In

<div align="center">

![FinLite Logo](https://img.shields.io/badge/FinLite-AI%20Assistant-blue)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Excel](https://img.shields.io/badge/Excel-Add--in-orange.svg)](https://docs.microsoft.com/en-us/office/dev/add-ins/)

*Intelligent Financial Data Analysis Excel Add-in - Bridging Excel and AI*

</div>

## Overview

FinLite AI Assistant is a VSTO-based Excel add-in that integrates Large Language Model (LLM) technology to provide intelligent financial data analysis and natural language question-answering capabilities. This project combines traditional Excel data processing with modern AI technology, enabling users to interact with Excel data through natural language queries.

**Development Background**: This project was developed by Clara Cen (UCL MSc Computer Science) under the supervision of Prof Dean Mohamedally and Prof Graham Roberts, in collaboration with Intel Corporation through the UCL Industry Exchange Network (UCL IXN).

## Key Features

### AI-Powered Data Analysis
- **Natural Language Queries**: Ask questions in plain English, and AI automatically analyzes Excel data
- **Intelligent Data Understanding**: Supports comprehension of financial terminology and professional concepts
- **Multiple Response Modes**: Concise, Detailed, and Formula explanation modes

### Excel Integration
- **Cell Selection Analysis**: Select specific data ranges for targeted analysis
- **Real-time Data Synchronization**: Automatically detects Excel data changes
- **Intelligent Workbook Recognition**: Supports multi-workbook and worksheet analysis

### Multimodal Interaction
- **Voice Input**: Click the microphone button for voice queries
- **Text Input**: Supports complex multi-line query input
- **Conversation History**: Automatically saves the latest 10 conversation sessions
- **Financial Analysis Specialization**: Comprehensive support for financial formula search and explanation

## Technical Architecture

### Frontend (Excel Add-in)
- **Development Framework**: VSTO (Visual Studio Tools for Office)
- **UI Technology**: WebView2 + HTML/CSS/JavaScript
- **UI Library**: Fluent UI Web Components
- **Programming Language**: C# (.NET Framework)

### Backend (AI Service)
- **Core Engine**: Python FastAPI
- **LLM Integration**: LLaMA.cpp + Granite-3.3-2B model
- **Vector Retrieval**: FAISS + sentence-transformers
- **Data Processing**: pandas + openpyxl
- **Hybrid Retrieval**: BM25 + Semantic vector retrieval

### Key Technical Components
```
Backend/
├── LLM Inference Engine (llama.cpp)
├── Hybrid Retrieval System (BM25 + Embedding)
├── Excel Data Processing (pandas)
├── API Service (FastAPI)
└── Conversation History Management

Excel Add-in/
├── Ribbon Interface (Office UI)
├── WebView2 Panel
├── Excel Interop
└── Voice Recognition Integration
```

## Installation Guide

### System Requirements
- **Operating System**: Windows 10/11
- **Excel Version**: Microsoft Excel 2016 or later

### Installation Steps

1. **Download the installer package** from our OneDrive link: [Download FinLite Setup](ONEDRIVE_LINK_HERE)
2. **Extract the downloaded ZIP file** to your desired location
3. **Run the installer** by double-clicking the MSI file
4. **Follow the installation wizard** to complete the setup
5. **Restart Excel** to activate the FinLite add-in

The add-in will appear in Excel's ribbon under the "FinLite" tab and pop up as a sidebar once installation is complete.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

</div>
