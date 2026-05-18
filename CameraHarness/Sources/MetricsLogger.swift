//
//  MetricsLogger.swift
//  
//
//  Created by Anthony Cano on 5/14/26.
//
import Foundation

// Func to add some more detailed metrics to the struct
func saveRun(capturedData: PhotoCaptureDelegate.CaptureData) throws {
    
    // Get the git_sha to keep track of which commits broke what or what improved things.
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/git")
    process.arguments = ["rev-parse", "--short", "HEAD"]
    
    let pipe = Pipe()
    process.standardOutput = pipe
    try process.run()
    process.waitUntilExit()

    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    let sha = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
    
    // `:` isn't valid in filenames on some filesystems, so swap for `-`.
    let timestamp = Date().formatted(.iso8601).replacingOccurrences(of: ":", with: "-")
    
    // Get the frame name so we can keep multiple pictures in the same commit.
    let frameFilename = "frame_\(timestamp)_\(sha ?? "unknown").jpg"
    
    // Save the relevant info we want!
    let runData: [String: Any] = [
        "timestamp": timestamp,
        "git_sha": sha ?? "Error: Missing",
        "device": Host.current().localizedName ?? "unknown",
        "device_os": "macOS",
        "os_version": ProcessInfo.processInfo.operatingSystemVersionString,
        "sample_frame": frameFilename,
        "metrics": [
            "jpeg_size_bytes": capturedData.jpegSizeBytes,
            "jpeg_width": capturedData.jpegWidth,
            "jpeg_height": capturedData.jpegHeight,
            "exif_iso": capturedData.exifISO,
            "exif_exposure_time": capturedData.exifExposureTime,
        ]
    ]
    
    // Convert dict to JSON!
    let jsonData = try JSONSerialization.data(withJSONObject: runData, options: .prettyPrinted)
    try jsonData.write(to: URL(fileURLWithPath: "RunData/\(timestamp)_\(sha ?? "unknown").json"))

    // Add the actual sample frame to JSON
    try capturedData.jpegData.write(to: URL(fileURLWithPath: "RunData/\(frameFilename)"))
}
