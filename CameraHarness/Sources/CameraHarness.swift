//
//  CameraHarness.swift
//
//  Created by Anthony Cano on 5/14/26.
//

import ArgumentParser

@main
struct CameraHarness: AsyncParsableCommand {

    func run() async throws {
        print("Starting....")
        try await CaptureRunner().startCapture()
    }
}
