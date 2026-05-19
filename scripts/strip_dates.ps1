$reportsDir = "d:/RAG view/reports"
$files = Get-ChildItem -Path $reportsDir -Filter "*.md"

foreach ($file in $files) {
    $lines = [System.IO.File]::ReadAllLines($file.FullName, [System.Text.Encoding]::UTF8)
    $newLines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in $lines) {
        $skip = $false
        foreach ($keyword in @("Step", "Phase", "Date", "Period", "Timeline", "Week")) {
            $pattern = "**" + $keyword + ":**"
            if ($line.StartsWith($pattern)) {
                $skip = $true
                break
            }
        }
        if (-not $skip) {
            $newLines.Add($line)
        }
    }
    [System.IO.File]::WriteAllLines($file.FullName, $newLines, [System.Text.Encoding]::UTF8)
    Write-Host "Cleaned: $($file.Name)"
}
