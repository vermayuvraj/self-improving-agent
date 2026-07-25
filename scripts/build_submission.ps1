# Assemble three self-contained LaTeX projects and zip them.
#
#   initial/  anonymous, 8-page body limit  -> icml2026-initial-submission.zip
#   camera/   de-anonymized, 9-page body    -> icml2026-camera-ready.zip
#   arxiv/    de-anonymized preprint        -> arxiv-preprint.zip
#
# Each zip is standalone: paper.tex, body.tex, references.bib, figures/ and the
# ICML style files, so Overleaf (or arXiv) compiles it with no extra setup.
#
# arXiv notes:
#   * icml2026.sty/.bst are NOT in TeX Live, so they must ship with the source.
#   * Figures are PDF, which is what arXiv requires for pdflatex mode; it does
#     no on-the-fly conversion.
#   * Files sit at the archive root, and no .aux/.log/.out/.blg/.pdf artifacts
#     are ever included — arXiv rejects intermediate files.

$ErrorActionPreference = "Stop"
$root   = Split-Path -Parent $PSScriptRoot
$paper  = Join-Path $root "PAPERS\capability-ablations"
$sub    = Join-Path $paper "submission"
$style  = Join-Path $paper "icml_style"

$styleFiles = @("icml2026.sty", "icml2026.bst", "fancyhdr.sty", "algorithm.sty", "algorithmic.sty")

# Intermediate/output files arXiv explicitly rejects. We never generate these
# locally, but guard anyway so a stray artifact can't slip into a zip.
$forbidden = @("*.aux", "*.log", "*.out", "*.blg", "*.toc", "*.synctex.gz", "*.fls", "*.fdb_latexmk")

$variants = @{
    "initial" = "icml2026-initial-submission"
    "camera"  = "icml2026-camera-ready"
    "arxiv"   = "arxiv-preprint"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem

# Windows PowerShell's Compress-Archive writes entry paths with BACKSLASHES,
# which violates the ZIP spec (4.4.17: forward slashes only). Overleaf tolerates
# it, but arXiv extracts on Linux and can read "figures\fig1.pdf" as a single
# literal filename, so the figures never land in a figures/ directory and the
# build fails with "file not found". Write entries ourselves with '/'.
function New-ZipWithPosixPaths {
    param([string]$SourceDir, [string]$ZipPath)

    if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
    $zip = [System.IO.Compression.ZipFile]::Open($ZipPath, "Create")
    try {
        $base = (Resolve-Path $SourceDir).Path.TrimEnd('\') + '\'
        foreach ($file in Get-ChildItem $SourceDir -Recurse -File) {
            $rel = $file.FullName.Substring($base.Length).Replace('\', '/')
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $zip, $file.FullName, $rel,
                [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
        }
    } finally {
        $zip.Dispose()
    }
}

foreach ($variant in @("initial", "camera", "arxiv")) {
    $dir = Join-Path $sub $variant
    if (-not (Test-Path $dir)) { throw "missing variant dir: $dir" }

    # body + bibliography, copied per-project so each zip stands alone
    Copy-Item (Join-Path $sub "body.tex")         $dir -Force
    Copy-Item (Join-Path $paper "references.bib") $dir -Force

    foreach ($f in $styleFiles) {
        Copy-Item (Join-Path $style $f) $dir -Force
    }

    # figures: PDF only (vector for LaTeX; the PNGs are for the web dashboard)
    $figDst = Join-Path $dir "figures"
    New-Item -ItemType Directory -Force $figDst | Out-Null
    Get-ChildItem (Join-Path $paper "figures\*.pdf") | Copy-Item -Destination $figDst -Force

    # strip any build artifacts before packaging
    foreach ($pat in $forbidden) {
        Get-ChildItem -Path $dir -Filter $pat -Recurse -File -ErrorAction SilentlyContinue |
            Remove-Item -Force
    }

    $zip = Join-Path $sub ($variants[$variant] + ".zip")
    New-ZipWithPosixPaths -SourceDir $dir -ZipPath $zip

    $n = (Get-ChildItem $dir -Recurse -File).Count
    "{0,-8} -> {1,-32} ({2,5:N0} KB, {3} files)" -f $variant, ($variants[$variant] + ".zip"),
        ((Get-Item $zip).Length / 1KB), $n
}

# Sanity: the anonymous submission must contain no identifying strings.
$initialTex = Get-Content (Join-Path $sub "initial\paper.tex") -Raw
$bodyTex    = Get-Content (Join-Path $sub "body.tex") -Raw
$leaks = @()
foreach ($pat in @("Yuvraj", "orcid", "0009-0004", "vermayuvraj")) {
    if ($initialTex -match [regex]::Escape($pat)) { $leaks += "initial/paper.tex: $pat" }
    if ($bodyTex    -match [regex]::Escape($pat)) { $leaks += "body.tex: $pat" }
}
if ($leaks.Count) {
    throw "ANONYMITY LEAK in initial submission -> $($leaks -join '; ')"
}
"`nanonymity check: initial submission is clean"
