<#
.SYNOPSIS
    Runs ClassSync Web PWA Playwright visual and interaction automation tests.
.DESCRIPTION
    Launches automated Chrome tests with support for Headed, UI Debugger, and Headless modes.
#>

param(
    [ValidateSet("headed", "ui", "headless")]
    [string]$Mode = "headed"
)

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "ClassSync: Automated Visual UI Testing Suite (Playwright + Chrome)" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

switch ($Mode) {
    "ui" {
        Write-Host "[1/1] Launching Playwright Interactive UI Debugger..." -ForegroundColor Green
        pnpm --filter web exec playwright test --ui
    }
    "headless" {
        Write-Host "[1/1] Running Playwright Headless Tests..." -ForegroundColor Green
        pnpm --filter web exec playwright test
    }
    Default {
        Write-Host "[1/1] Launching Headed Chrome Window for Visual Observation..." -ForegroundColor Green
        pnpm --filter web exec playwright test --headed
    }
}
