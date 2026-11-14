<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class GifController extends Controller
{
    public function create(Request $request)
    {
        // 1. Validation
        if (!$request->hasFile('images') || !$request->has('targetSize')) {
            return response()->json(['error' => 'Missing required fields: images and targetSize'], 400);
        }

        $images = $request->file('images');
        if (!is_array($images)) {
            return response()->json(['error' => 'images must be an array of files'], 400);
        }

        $targetSize = $request->input('targetSize'); // e.g. "500x500"
        $delay = (int) $request->input('delay', 10);
        $appendReverted = filter_var($request->input('appendReverted'), FILTER_VALIDATE_BOOLEAN);

        // Validate targetSize format (widthxheight)
        if (!preg_match('/^\d+x\d+$/', $targetSize)) {
            return response()->json(['error' => 'targetSize must be in format WxH (e.g. 500x500)'], 400);
        }

        $tempDir = storage_path('app/gif_temp_' . uniqid());
        File::makeDirectory($tempDir, 0777, true);

        try {
            $inputFiles = [];
            foreach ($images as $index => $file) {
                $filename = "frame_{$index}.jpg";
                $path = $tempDir . '/' . $filename;
                $file->move($tempDir, $filename);
                $inputFiles[] = $path;
            }

            // Handle "appendReverted" logic
            if ($appendReverted) {
                $reverted = array_reverse($inputFiles);
                $inputFiles = array_merge($inputFiles, $reverted);
            }

            $outputFile = $tempDir . '/result.gif';
            
            // ImageMagick command construction
            // -delay is in hundredths of a second (10ms = 0.1, but IM uses 1/100s units)
            // The schema says delay is in ms. IM delay is 1/100s. 
            // So 100ms = 10 units of delay.
            $imDelay = $delay / 10;
            
            $filesString = implode(' ', array_map('escapeshellarg', $inputFiles));
            $cmd = sprintf(
                'convert -delay %f -loop 0 -resize %s %s %s',
                $imDelay,
                escapeshellarg($targetSize),
                $filesString,
                escapeshellarg($outputFile)
            );

            exec($cmd, $output, $returnVar);

            if ($returnVar !== 0) {
                throw new \Exception("ImageMagick conversion failed");
            }

            // Return the GIF file
            return new BinaryFileResponse($outputFile, 200, [
                'Content-Type' => 'image/gif',
                'Content-Disposition' => 'inline; filename="animation.gif"'
            ]);

        } catch (\Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        } finally {
            // Note: In a production environment, we would use a queued job to clean up 
            // the temp directory after the response is sent. 
            // For this exercise, we accept the temp files or use a cleanup script.
        }
    }
}