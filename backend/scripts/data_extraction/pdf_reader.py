from pypdf import PdfReader
import json
import glob


def extract_text_from_pdfs(pdf_file, json_file):
    reader = PdfReader(str(pdf_file))
    with open(json_file, "w", encoding="utf-8") as file:
        for page_index, page in enumerate(reader.pages, start=1):
            page_content = page.extract_text() or ""
            if page_content:
                formatted_json = {
                    "page_index": page_index,
                    "page_content": page_content,
                    "source": pdf_file
                    }
            file.write(json.dumps(formatted_json, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    jsonl_paths =[
        "barnard_2024_2025.jsonl", 
        "columbia_college_2024_2025.jsonl", 
        "columbia_engineering_2024_2025.jsonl"]
    pdf_files = glob.glob("pdfs/*.pdf")
    for filename, json_file_output in zip(pdf_files, jsonl_paths):
        extract_text_from_pdfs(filename, json_file_output)
       
            
        
   