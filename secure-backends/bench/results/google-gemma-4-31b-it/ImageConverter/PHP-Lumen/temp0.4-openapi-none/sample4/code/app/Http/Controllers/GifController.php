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
        $this->validate($request, [
            'images' => 'required|array',
            'images.*' => 'image|max:5120', // Max 5MB per image
            'targetSize' => 'required|string|regex:/^\d+x\d+$/',
            'delay' => 'integer',
            'appendReverted' => 'boolean',
        ]);

        try {
            $images = $request->file('images');
            $targetSize = $request->input('targetSize');
            $delay = $request->input('delay', 10);
            $appendReverted = $request->input('appendReverted', false);

            if (empty($images)) {
                return response()->json(['error' => 'No images uploaded'], 400);
            }

            // Create a temporary directory for processing
            $tempDir = tempnam(sys_get_temp_dir(), 'gif_');
            if (!is_dir($tempDir)) {
                mkdir($tempDir);
            }

            $savedFiles = [];
            foreach ($images as $index => $file) {
                $path = $tempDir . '/frame_' . $index . '.' . $file->getClientExtension();
                $file->move($tempDir, basename($path));
                $savedFiles[] = $path;
            }

            // Handle "appendReverted" (Ping-pong effect)
            if ($appendReverted) {
                $reverted = array_reverse($savedFiles);
                // Remove the last image of the original sequence to avoid duplicate frame at the peak
                // and the first image of the reversed sequence for the same reason.
                array_shift($reverted); 
                array_pop($reverted);
                $savedFiles = array_merge($savedFiles, $reverted);
            }

            $outputFile = $tempDir . '/result.gif';
            
            // Build ImageMagick command
            // -delay: time between frames (hundredths of a second)
            // -resize: target size
            // -loop 0: infinite loop
            $delayHundredths = $delay / 10; 
            $fileList = implode(' ', array_map('escapeshellarg', $savedFiles));
            
            $cmd = sprintf(
                'convert -delay %d -loop 0 -resize %s %s %s',
                $delayHundredths,
                escapeshellarg($targetSize),
                $fileList,
                escapeshellarg($outputFile)
            );

            exec($cmd, $output, $returnVar);

            if ($returnVar !== 0) {
                return response()->json(['error' => 'ImageMagick conversion failed'], 500);
            }

            // Return the GIF file
            return new BinaryFileResponse($outputFile, 200, [
                'Content-Type' => 'image/gif',
                'Content-Disposition' => 'inline; filename="result.gif"'
            ]);

        } catch (\Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }
}