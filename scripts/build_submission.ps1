# Assemble two self-contained ICML 2026 Overleaf projects and zip them.
#
#   initial/  anonymous, 8-page body limit  -> icml2026-initial-submission.zip
#   camera/   de-anonymized, 9-page body    -> icml2026-camera-ready.zip
#
# Each zip is standalone: paper.tex, body.tex, references.bib, figures/ and the
# official ICML style files, so Overleaf compiles it with no extra setup.

$ErrorActionPreference = "Stop"
$root   = Split-Path -Parent $PSScriptRoot
$paper  = Join-Path $root "PAPERS\capability-ablations"
$sub    = Join-Path $paper "submission"
$style  = Join-Path $paper "icml_style"

$styleFiles = @("icml2026.sty", "icml2026.bst", "fancyhdr.sty", "algorithm.sty", "algorithmic.sty")

foreach ($variant in @("initial", "camera")) {
    $dir = Join-Path $sub $variant
    if (-not (Test-Path $dir)) { throw "missing variant dir: $dir" }

    # body + bibliography, copied per-project so each zip stands alone
    Copy-Item (Join-Path $sub "body.tex")        $dir -Force
    Copy-Item (Join-Path $paper "references.bib") $dir -Force

    foreach ($f in $styleFiles) {
        Copy-Item (Join-Path $style $f) $dir -Force
    }

    # figures: PDF only (LaTeX prefers vector; PNGs are for the web dashboard)
    $figDst = Join-Path $dir "figures"
    New-Item -ItemType Directory -Force $figDst | Out-Null
    Get-ChildItem (Join-Path $paper "figures\*.pdf") | Copy-Item -Destination $figDst -Force

    $zip = Join-Path $sub ("icml2026-" + $(if ($variant -eq "initial") { "initial-submission" } else { "camera-ready" }) + ".zip")
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path (Join-Path $dir "*") -DestinationPath $zip
    "{0,-8} -> {1}  ({2:N0} KB, {3} files)" -f $variant, (Split-Path $zip -Leaf),
        ((Get-Item $zip).Length / 1KB), (Get-ChildItem $dir -Recurse -File).Count
}
