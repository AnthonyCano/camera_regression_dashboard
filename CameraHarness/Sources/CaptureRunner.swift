//
//  CaptureRunner.swift
//  
//
//  Created by Anthony Cano on 5/14/26.
//
import AVFoundation
import Foundation
import ImageIO
import CoreGraphics

class PhotoCaptureDelegate: NSObject, AVCapturePhotoCaptureDelegate {
    
    struct CaptureData{
        let jpegSizeBytes: Int
        let jpegWidth: Int
        let jpegHeight: Int
        let exifISO: Int
        let exifExposureTime: Double
        let jpegData: Data
    }
    
    var onCapture: ((CaptureData) -> Void)?
    
    
    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        // Okay so we need to get the info we want.
        if error == nil {
            guard let jpegData = photo.fileDataRepresentation() else {
                print("Failed to get JPEG data")
                return
            }
            guard let imageSource = CGImageSourceCreateWithData(jpegData as CFData, nil) else{
                print("Failed to get IMG source")
                return
            }
            
            let properties = CGImageSourceCopyPropertiesAtIndex(imageSource, 0 , nil) as? [String: Any]
            let exifDict = properties?[kCGImagePropertyExifDictionary as String] as? [String: Any]
            let expsoureTime = exifDict?[kCGImagePropertyExifExposureTime as String] as? Double
            let iso = exifDict?[kCGImagePropertyExifISOSpeedRatings as String] as? [Int]
            let width = properties?[kCGImagePropertyPixelWidth as String] as? Int
            let height = properties?[kCGImagePropertyPixelHeight as String] as? Int
            
            let capture = CaptureData(
                jpegSizeBytes: jpegData.count,
                jpegWidth: width ?? 0,
                jpegHeight: height ?? 0,
                exifISO: iso?.first ?? 0,
                exifExposureTime: expsoureTime ?? 0.0,
                jpegData: jpegData
            )
            
            onCapture?(capture)
            
        }
    }
}

struct CaptureRunner {

    private var isAuthorized: Bool {
        get async {
            let status = AVCaptureDevice.authorizationStatus(for: .video)
            var isAuthorized = status == .authorized
            if status == .notDetermined {
                isAuthorized = await AVCaptureDevice.requestAccess(for: .video)
            }
            return isAuthorized
        }
    }

    // Func to start the capture session
    func startCapture() async throws {

        guard await isAuthorized else {
            print("Camera access denied. Grant access in System Settings > Privacy & Security > Camera, then re-run.")
            return
        }

        let captureSession = AVCaptureSession()
        guard let videoDevice = AVCaptureDevice.default(for: .video) else {
            print("No video device found")
            exit(1)
        }
        
        
        do {
            let videoInput = try AVCaptureDeviceInput(device: videoDevice)
            // Use the videoInput here however is needed
            
            if captureSession.canAddInput(videoInput) {
                captureSession.addInput(videoInput)
                
                // Now create a videoOutput object
                let photoOutput = AVCapturePhotoOutput()
                if captureSession.canAddOutput(photoOutput) {
                    captureSession.addOutput(photoOutput)
                }
                
                // Start the session
                captureSession.startRunning()
                // add a buffer for the camera to adjust
                try await Task.sleep(nanoseconds: 2_000_000_000)
                
                let settings = AVCapturePhotoSettings(format: [AVVideoCodecKey: AVVideoCodecType.jpeg])
                
                // create the delegate instance
                let delegate = PhotoCaptureDelegate()

                // Suspend until the photo callback fires
                let captureData: PhotoCaptureDelegate.CaptureData = await withCheckedContinuation { continuation in
                    delegate.onCapture = { data in
                        continuation.resume(returning: data)
                    }
                    photoOutput.capturePhoto(with: settings, delegate: delegate)
                }

                print("Got JPEG: \(captureData.jpegSizeBytes) bytes")
                // Pass to the metrics logger!
                do {
                    try saveRun(capturedData: captureData)

                } catch {
                    print("Failed to save the run....")
                }
                
            }
        } catch {
            // Error has occured.
            print("Failed to create video input: \(error.localizedDescription)")
            return
        }
        
    }
}
