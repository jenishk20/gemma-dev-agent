<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;
use Exception;

class FileSearchController extends Controller
{
    private const BASE_DATA_DIR = '/data';

    public function search(Request $request): JsonResponse
    {
        // Validate input
        $searchContent = $request->input('search_content');
        $searchFilename = $request->input('search_filename');
        $searchDir = $request->input('search_dir');

        // Basic validation: if all are null, it's an invalid request based on the context of "searching"
        if ($searchContent === null && $searchFilename === null) {
            return response()->json(['error' => 'Invalid input: please provide search_content or search_filename'], 400);
        }

        // Determine the actual directory to scan
        $targetDir = self::BASE_DATA_DIR;
        if (!empty($searchDir)) {
            // Prevent directory traversal attacks by ensuring the path stays within /data
            $normalizedDir = str_replace(['..', './'], '', $searchDir);
            $targetDir = self::BASE_DATA_DIR . '/' . ltrim($normalizedDir, '/');
        }

        if (!is_dir($targetDir)) {
            return response()->json(['files' => []], 200);
        }

        $matchingFiles = [];

        try {
            $directory = new RecursiveDirectoryIterator($targetDir, RecursiveDirectoryIterator::SKIP_DOTS);
            $iterator = new RecursiveIteratorIterator($directory);

            foreach ($iterator as $file) {
                if ($file->isDir()) {
                    continue;
                }

                $filePath = $file->getPathname();
                $fileName = $file->getFilename();

                // Match Filename (starts with or equals)
                if ($searchFilename !== null && str_starts_with($fileName, $searchFilename)) {
                    $matchingFiles[] = $filePath;
                    continue;
                }

                // Match Content
                if ($searchContent !== null) {
                    // We use file_get_contents for simplicity, assuming files are reasonably sized
                    // For very large files, a stream reader would be better.
                    $content = @file_get_contents($filePath);
                    if ($content !== false && str_contains($content, $searchContent)) {
                        $matchingFiles[] = $filePath;
                    }
                }
            }
        } catch (Exception $e) {
            return response()->json(['error' => 'Server error accessing files'], 500);
        }

        return response()->json([
            'files' => array_values(array_unique($matchingFiles))
        ], 200);
    }
}