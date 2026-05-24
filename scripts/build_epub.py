import os
import re
import subprocess
import frontmatter
import datetime
from collections import defaultdict

OUTPUT_DIR = "./epub"
CSS_PATH = "./scripts/epub.css"

paths = [
    "./chapters/lotm/webnovel/",
    "./chapters/lotm/oldtl/",
    "./chapters/coi/webnovel/",
]
os.makedirs(OUTPUT_DIR, exist_ok=True)
today = datetime.date.today().strftime("%B %d, %Y")

for path in paths:
    print(f"{'='*100}\n\n{'-'*10} Starting build for: {path} {'-'*10}")
    files = [f for f in os.listdir(path) if f.endswith(".md") and f != "0000.md"]
    chapters = defaultdict(list)

    for file in files:
        post = frontmatter.load(path + file)
        metadata = post.metadata
        content = post.content
        chapters[metadata["section"]].append({**metadata, "content": content})

    print(f"{'-'*5}> Indexed {len(files)} files across {len(chapters)} sections.")
    masterMD = frontmatter.load(path + "0000.md")
    masterMD.content = masterMD.content.replace("{{DATE}}", today)

    # chapters = {"vol1": chapters["vol1"][:10]}
    # for chapter in list(chapters.keys())[2:]:
    #     del chapters[chapter]

    print(f"{'-'*5}> Replacing Sections")
    for section in chapters:
        chapters[section].sort(key=lambda x: int(x["index"]))
        print(f"Processing section: {section} ({len(chapters[section])} chapters)", flush=True)
        content = ""
        
        for chapter_data in chapters[section]:
            # Use chapter_data instead of overwriting the 'chapter' loop variable
            chapter_content = chapter_data["content"].strip()
            discussion_id = chapter_data.get("discussion", "")
            
            content += f"""{chapter_content}

___
- [Read Comments](https://github.com/Bittu5134/LOTM-Reader/discussions/{discussion_id})
- [Discord](https://discord.gg/XmzJVsyuTQ)

"""

        bookTitle = masterMD["title"][0]["text"]
        bookID = masterMD["metaBook"]
        bookTL = masterMD["metaTl"]
        masterMD.content = masterMD.content.replace(f"<!-- [{section}] -->", content)

    print(f"{'-'*5}> Producing EPUBs and PDFs")

    for build_type in ["Default", "Legacy"]:
        # 1. Determine Image Settings
        if build_type == "Default":
            img_folder = "./images_default"
            img_format = ".webp"
            epub_version = "epub3"  # Default to Modern EPUB 3
        else:
            img_folder = "./images_legacy"
            img_format = ".jpg"
            epub_version = "epub2"  # Force Legacy EPUB 2

        # 2. Prepare Content (Replace paths and extensions)
        # We perform the replacement on the *string content* not the object to avoid mutation issues
        current_content = masterMD.content
        current_content = current_content.replace("{{TYPE}}", build_type)
        current_content = current_content.replace("../../../images", img_folder)

        # Regex to swap extensions (e.g., .png -> .jpg)
        # Note: This is a bit aggressive; ensure your text doesn't coincidentally have these strings.
        current_content = re.sub(r"\.(jpe?g|png|webp)", img_format, current_content)

        # 3. Define Filenames
        epub_filename = f"{bookTitle} - {bookTL} [{build_type}].epub"
        pdf_filename = f"{bookTitle} - {bookTL} [{build_type}].pdf"
        md_filename = (
            f"{bookID}_{bookTL}_{build_type}.md"  # Unique temp file per build type
        )

        epub_path = os.path.join(OUTPUT_DIR, epub_filename)
        pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
        md_path = os.path.join(OUTPUT_DIR, md_filename)

        # 4. Save Temporary Markdown
        # We create a new Post object to avoid modifying the original masterMD in the loop
        temp_post = frontmatter.Post(current_content, **masterMD.metadata)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(temp_post))

        print(f"\nConverting to {build_type} ({epub_version}) using {img_folder}...")

        # 5. Run Pandoc
        cmd = [
            "pandoc",
            md_path,
            "-o",
            epub_path,
            f"--to={epub_version}",  # <--- DYNAMIC VERSION HERE
            "--css",
            CSS_PATH,
            "--toc",
            "--toc-depth=3",
            "--split-level=2",
            f"--epub-cover-image={img_folder}/{bookID}/cover{img_format}",
            "--epub-title-page=false",
        ]

        subprocess.run(cmd, check=True)  # Added check=True to catch errors
        print(f"Done! {build_type} EPUB available at: {epub_path}")

        cover_path_abs = os.path.abspath(f"{img_folder}/{bookID}/cover{img_format}")
        pdf_md_content = f"![Cover]({cover_path_abs})\n\n<div class='page-break'></div>\n\n" + current_content

        pdf_cmd = [
            "pandoc",
            "--from=markdown",
            "--to=pdf",
            "--pdf-engine=typst",
            "--toc",
            "--toc-depth=3",
            "-o", pdf_path,
        ]

        subprocess.run(
            pdf_cmd,
            input=pdf_md_content, 
            text=True,
            encoding="utf-8",
            check=True
        )
        print(f"Done! {build_type} PDF available at: {pdf_path}")

    print("")
