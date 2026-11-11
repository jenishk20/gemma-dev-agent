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

        // If all are null, we can't search for anything specific
        if ($searchContent === null && $searchFilename === null) {
            return response()->json(['error' => 'Invalid input: provide search_content or search_filename'], 400);
        }

        // Resolve the directory to search in
        $rootPath = self::BASE_DATA_DIR;
        if (!empty($searchDir)) {
            // Ensure search_dir is treated as relative to /data to prevent directory traversal
            $searchDir = trim($searchDir, '/');
            $rootPath = self::BASE_DATA_DIR . DIRECTORY_SEPARATOR . $searchDir;
        }

        if (!is_dir($rootPath)) {
            return response()->json(['files' => []], 200);
        }

        $matchingFiles = [];

        try {
            $directory = new RecursiveDirectoryIterator($rootPath, RecursiveDirectoryIterator::SKIP_DOTS);
            $iterator = new RecursiveIteratorIterator($directory);

            foreach ($iterator as $file) {
                if ($file->isDir()) {
                    continue;
                }

                $filePath = $file->getPathname();
                $fileName = $file->getFilename();

                $match = false;

                // Match by filename (starts with or equals)
                if ($searchFilename !== null && str_starts_with($fileName, $searchFilename)) {
                    $match = true;
                }

                // Match by content
                if (!$match && $searchContent !== null) {
                    // We use file_get_contents for simplicity, but in production, 
                    // a stream reader would be better for very large files.
                    $content = @file_get_contents($filePath);
                    if ($content !== false && str_contains($content, $searchContent)) {
                        $match = true;
                    }
                }

                if ($match) {
                    $matchingFiles[] = $filePath;
                }
            }
        } catch (Exception $e) {
            return response()->json(['error' => 'Server error accessing files'], 500);
        }

        return response()->json([
            'files' => $matchingFiles
        ], 200);
    }
}