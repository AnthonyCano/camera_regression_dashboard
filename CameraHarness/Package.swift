// swift-tools-version: 5.9
//
//  Package.swift
//
//  Created by Anthony Cano on 5/14/26.
//

import PackageDescription

let package = Package(
    name: "CameraHarness",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "CameraHarness", targets: ["CameraHarness"])
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-argument-parser", from: "1.3.0"),
    ],
    targets: [
        .executableTarget(
            name: "CameraHarness",
            dependencies: [
                .product(name: "ArgumentParser", package: "swift-argument-parser"),
            ],
            path: "Sources",
            linkerSettings: [
                .unsafeFlags([
                    "-Xlinker", "-sectcreate",
                    "-Xlinker", "__TEXT",
                    "-Xlinker", "__info_plist",
                    "-Xlinker", "Info.plist",
                ])
            ]
        )
    ]
)
