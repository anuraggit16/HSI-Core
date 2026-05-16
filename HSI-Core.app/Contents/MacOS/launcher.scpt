#!/usr/bin/env osascript
-- HSI-Core macOS App Launcher
-- Double-click this in Finder to launch
-- This AppleScript will run the HSI-Core system

on run
    set baseDir to POSIX path of (path to me)
    set baseDir to text 1 thru ((offset of ".app" in baseDir) - 1) of baseDir
    
    -- Show startup message
    display notification "HSI-Core is starting up..." with title "Hyperspectral Imaging System"
    
    -- Open Terminal and run launcher
    tell application "Terminal"
        activate
        do script "cd '" & baseDir & "' && bash RUN_HSI_CORE.command"
    end tell
end run
