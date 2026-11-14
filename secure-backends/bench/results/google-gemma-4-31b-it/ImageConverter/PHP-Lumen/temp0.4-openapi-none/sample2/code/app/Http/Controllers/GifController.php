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
            'images.*' => 'required|image',
            'targetSize' => 'required|string|regex:/^\d+x\d+$/',
            'delay' => 'integer',
            'appendReverted' => 'boolean',
        ]);

        $images = $request->file('images');
        $targetSize = $request->input('targetSize');
        $delay = $request->input('delay', 10);
        $appendReverted = $request->input('appendReverted', false);

        if (empty($images)) {
            return response()->json(['error' => 'No images provided'], 400);
        }

        try {
            $tempDir = storage_path('app/gif_temp_' . uniqid());
            if (!File::exists($tempDir)) {
                File::makeDirectory($tempDir, 0777, true);
            }

            $savedFiles = [];
            foreach ($images as $index => $file) {
                $path = $tempDir . "/frame_{$index}.jpg";
                $file->move($tempDir, "frame_{$index}.jpg");
                $savedFiles[] = $path;
            }

            // Handle appendReverted: duplicate the list in reverse order
            if ($appendReverted) {
                $revertedFiles = array_reverse($savedFiles);
                // To avoid duplicate filenames if the list is small, 
                // we just add them to the command sequence
                $finalSequence = array_merge($savedFiles, $revertedFiles);
            } else {
                $finalSequence = $savedFiles;
            }

            $outputFile = $tempDir . '/result.gif';
            
            // ImageMagick Command Construction
            // -delay is in hundredths of a second (100ms = 10)
            // We convert ms to ImageMagick units: delay / 10
            $imDelay = (int)($delay / 10);
            
            $cmd = sprintf(
                'convert -delay %d -loop 0 -resize %s %s result.gif',
                $imDelay,
                escapeshellarg($targetSize),
                implode(' ', array_map('escapeshellarg', $finalSequence))
            );

            // The output file is inside the tempDir, so we need to change directory or specify full path
            // Using -out or specifying full path for the result
            $cmd = sprintf(
                'convert -delay %d -loop 0 -resize %s %s %s',
                $imDelay,
                escapeshellarg($targetSize),
                implode(' ', array_map('escapeshellarg', $finalSequence)),
                escapeshellarg($outputFile)
            );

            exec($cmd, $output, $returnVar);

            if ($returnVar !== 0) {
                throw new \Exception("ImageMagick conversion failed");
            }

            // Return the file as a GIF response
            return new BinaryFileResponse($outputFile, 200, [
                'Content-Type' => 'image/gif',
                'Content-Disposition' => 'inline; filename="animation.gif"'
            ]);

        } catch (\Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }
}