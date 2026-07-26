# Build the arXiv preprint package, compile it locally, and zip it.
#
# Produces the flat layout arXiv expects:
#
#   main.tex      single self-contained source (body.tex inlined at build time)
#   main.bbl      pre-generated bibliography; arXiv uses it verbatim
#   refs.bib      kept for reference/reproducibility
#   figures/*.pdf vector figures (arXiv does no on-the-fly conversion)
#   *.sty, *.bst  the ICML style files, which are NOT in TeX Live
#
# The .bbl basename MUST match the main .tex basename, hence main.tex/main.bbl.
#
# Requires MiKTeX (pdflatex + bibtex) so the package is verified to compile
# before shipping. Run:  powershell -ExecutionPolicy Bypass -File scripts\build_arxiv.ps1

$ErrorActionPreference = "Stop"

$root   = Split-Path -Parent $PSScriptRoot
$paper  = Join-Path $root "PAPERS\capability-ablations"
$sub    = Join-Path $paper "submission"
$style  = Join-Path $paper "icml_style"
$stage  = Join-Path $sub "arxiv-package"
$zip    = Join-Path $sub "arxiv-preprint.zip"

$tex = "C:\Users\Yuvraj Verma\AppData\Local\Programs\MiKTeX\miktex\bin\x64"
$pdflatex = Join-Path $tex "pdflatex.exe"
$bibtex   = Join-Path $tex "bibtex.exe"
foreach ($exe in @($pdflatex, $bibtex)) {
    if (-not (Test-Path $exe)) { throw "missing TeX binary: $exe" }
}

# --- stage -----------------------------------------------------------------
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null
New-Item -ItemType Directory -Force (Join-Path $stage "figures") | Out-Null

# main.tex = arxiv/paper.tex with the body inlined and the bib renamed, so the
# archive is a single source file while the repo keeps one shared body.tex.
$src  = Get-Content (Join-Path $sub "arxiv-main-template.tex") -Raw
$body = Get-Content (Join-Path $sub "body.tex") -Raw
# Literal replaces, not regex: TeX is full of backslashes that regex would eat.
$main = $src.Replace("\input{body}", $body).Replace("\bibliography{references}", "\bibliography{refs}")
if ($main.Contains("\input{body}")) { throw "body inlining failed" }
if (-not $main.Contains("\bibliography{refs}")) { throw "bibliography rename failed" }
Set-Content (Join-Path $stage "main.tex") $main -Encoding UTF8 -NoNewline

Copy-Item (Join-Path $paper "references.bib") (Join-Path $stage "refs.bib") -Force
foreach ($f in @("icml2026.sty", "icml2026.bst", "fancyhdr.sty", "algorithm.sty", "algorithmic.sty")) {
    Copy-Item (Join-Path $style $f) $stage -Force
}
Get-ChildItem (Join-Path $paper "figures\*.pdf") | Copy-Item -Destination (Join-Path $stage "figures") -Force

# --- compile (pdflatex, bibtex, pdflatex x2) so main.bbl exists and is valid --
Push-Location $stage
try {
    # MiKTeX prints an "unchecked for updates" notice on stderr; with
    # ErrorActionPreference=Stop PowerShell would escalate that into a
    # terminating error, so relax it here and judge success by exit code and
    # by whether the expected artifacts appear.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $pdflatex -interaction=nonstopmode main.tex | Out-Null
    & $bibtex main | Out-Null
    $bibtexExit = $LASTEXITCODE
    & $pdflatex -interaction=nonstopmode main.tex | Out-Null
    & $pdflatex -interaction=nonstopmode main.tex | Out-Null
    $pdflatexExit = $LASTEXITCODE
    $ErrorActionPreference = $prev
    "pdflatex exit=$pdflatexExit  bibtex exit=$bibtexExit"
} finally {
    Pop-Location
}

if (-not (Test-Path (Join-Path $stage "main.bbl"))) { throw "bibtex produced no main.bbl" }
if (-not (Test-Path (Join-Path $stage "main.pdf"))) { throw "pdflatex produced no main.pdf" }

$pdfPages = (Select-String -Path (Join-Path $stage "main.log") -Pattern 'Output written .*\((\d+) pages' -EA SilentlyContinue).Matches.Groups[1].Value
$undef = (Select-String -Path (Join-Path $stage "main.log") -Pattern 'Citation .* undefined|LaTeX Warning: Reference .* undefined' -EA SilentlyContinue).Count
$bblRefs = (Select-String -Path (Join-Path $stage "main.bbl") -Pattern '^\\bibitem' -EA SilentlyContinue).Count

"compiled: $pdfPages pages, $bblRefs bibliography entries, $undef undefined refs/citations"

# Keep a copy of the built PDF outside the package for inspection.
Copy-Item (Join-Path $stage "main.pdf") (Join-Path $sub "arxiv-preview.pdf") -Force

# --- strip build artifacts (arXiv rejects them); keep main.bbl ---------------
foreach ($pat in @("*.aux", "*.log", "*.out", "*.blg", "*.toc", "*.pdf",
                   "*.synctex.gz", "*.fls", "*.fdb_latexmk", "_build.txt")) {
    Get-ChildItem -Path $stage -Filter $pat -File -EA SilentlyContinue | Remove-Item -Force
}

# --- zip with POSIX separators (Compress-Archive writes backslashes, which
#     Linux extraction on arXiv can read as literal filenames) ---------------
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (Test-Path $zip) { Remove-Item $zip -Force }
$archive = [System.IO.Compression.ZipFile]::Open($zip, "Create")
try {
    $base = (Resolve-Path $stage).Path.TrimEnd('\') + '\'
    foreach ($file in Get-ChildItem $stage -Recurse -File | Sort-Object FullName) {
        $rel = $file.FullName.Substring($base.Length).Replace('\', '/')
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $archive, $file.FullName, $rel,
            [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
} finally { $archive.Dispose() }

"`narxiv-preprint.zip contents:"
$z = [System.IO.Compression.ZipFile]::OpenRead($zip)
$z.Entries | Sort-Object FullName | ForEach-Object { "  {0,-28} {1,8:N0} B" -f $_.FullName, $_.Length }
$z.Dispose()
"`nwrote {0} ({1:N0} KB)" -f $zip, ((Get-Item $zip).Length / 1KB)
"preview PDF: $sub\arxiv-preview.pdf"
