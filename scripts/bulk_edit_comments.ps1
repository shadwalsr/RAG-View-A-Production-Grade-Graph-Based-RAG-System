# PowerShell script to shorten comments across the RagView project
# Save as scripts/bulk_edit_comments.ps1

$projectRoot = "d:/RAG view"
$maxLen = 80

function Shorten-Comment($text) {
    $periodIdx = $text.IndexOf('.')
    if ($periodIdx -gt 0) {
        $short = $text.Substring(0, $periodIdx + 1).Trim()
    } else {
        $trimmed = $text.Trim()
        if ($trimmed.Length -gt $maxLen) {
            $short = $trimmed.Substring(0, $maxLen).Trim()
        } else {
            $short = $trimmed
        }
        if (-not $short.EndsWith('.')) { $short = "$short." }
    }
    return $short
}

$patterns = @("*.py","*.js","*.ts","*.tsx","*.jsx","*.html","*.css")

Get-ChildItem -Path $projectRoot -Recurse -Include $patterns -File | ForEach-Object {
    $filePath = $_.FullName
    $content = Get-Content -Path $filePath -Raw -Encoding utf8
    $lines = $content -split "`n"
    $modified = $false
    $newLines = foreach ($line in $lines) {
        $trim = $line.TrimStart()
        if ($trim.StartsWith('#')) {
            $prefix = $line.Substring(0, $line.Length - $trim.Length)
            $comment = $trim.Substring(1).Trim()
            if ($comment) {
                $short = Shorten-Comment $comment
                $newLine = "$prefix# $short"
                if ($newLine -ne $line) { $modified = $true }
                $newLine
            } else { $line }
        } elseif ($trim.StartsWith('//')) {
            $prefix = $line.Substring(0, $line.Length - $trim.Length)
            $comment = $trim.Substring(2).Trim()
            if ($comment) {
                $short = Shorten-Comment $comment
                $newLine = "$prefix// $short"
                if ($newLine -ne $line) { $modified = $true }
                $newLine
            } else { $line }
        } elseif ($trim.StartsWith('/*')) {
            # handle single-line block comment
            $endIdx = $trim.IndexOf('*/')
            if ($endIdx -gt -1) {
                $prefix = $line.Substring(0, $line.Length - $trim.Length)
                $inner = $trim.Substring(2, $endIdx - 2).Trim()
                $short = Shorten-Comment $inner
                $newLine = "$prefix/* $short */"
                if ($newLine -ne $line) { $modified = $true }
                $newLine
            } else {
                # multi-line block: replace first line only
                $prefix = $line.Substring(0, $line.Length - $trim.Length)
                $inner = $trim.Substring(2).Trim()
                $short = Shorten-Comment $inner
                $newLine = "$prefix/* $short */"
                $modified = $true
                $newLine
            }
        } elseif ($trim.StartsWith('<!--')) {
            $prefix = $line.Substring(0, $line.Length - $trim.Length)
            $inner = $trim.Substring(4).Split('-->',2)[0].Trim()
            $short = Shorten-Comment $inner
            $newLine = "$prefix<!-- $short -->"
            if ($newLine -ne $line) { $modified = $true }
            $newLine
        } else {
            $line
        }
    }
    if ($modified) {
        $newContent = $newLines -join "`n"
        Set-Content -Path $filePath -Value $newContent -Encoding utf8
        Write-Host "Updated comments in $filePath"
    }
}

# Delete the old Python helper script if it exists
$oldScript = Join-Path $projectRoot "scripts\update_comments.py"
if (Test-Path $oldScript) { Remove-Item $oldScript -Force }
