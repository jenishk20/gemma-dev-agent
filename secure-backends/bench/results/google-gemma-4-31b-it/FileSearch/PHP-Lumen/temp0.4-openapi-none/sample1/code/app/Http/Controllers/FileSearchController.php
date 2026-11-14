<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;

class FileSearchController extends Controller
{
    public function search(Request $request)
    {
        // Validate input
        $this->validate($request, [
            'search_content' => 'nullable|string',
            'search_filename' => 'nullable|string',
            'search_dir' => 'nullable|string',
        ]);

        $searchContent = $request->input('search_content');
        $searchFilename = $request->input('search_filename');
        $searchDirRelative = $request->input('search_dir');

        // Base directory is /data
        $baseDir = '/data';
        
        // Resolve the actual directory to search in
        $targetDir = $baseDir;
        if (!empty($searchDirRelative)) {
            $targetDir = rtrim($baseDir, '/') . '/' . ltrim($searchDirRelative, '/');
        }

        if (!is_dir($targetDir)) {
            return response()->json(['error' => 'Search directory not found'], 400);
        }

        $matchedFiles = [];

        try {
            $directory = new RecursiveDirectoryIterator($targetDir);
            $iterator = new RecursiveIteratorIterator($directory);

            foreach ($iterator as $file) {
                if ($file->isDir()) {
                    continue;
                }

                $filePath = $file->getPathname();
                $fileName = $file->getFilename();

                // Match by filename (starts with or equals)
                if (!empty($searchFilename)) {
                    if (str_starts_with($fileName, $searchFilename)) {
                        $matchedFiles[] = $filePath;
                        continue; // Move to next file if filename matches
                    }
                }

                // Match by content
                if (!empty($searchContent)) {
                    // We use file_get_contents for simplicity, but in production, 
                    // one might use a stream for very large files.
                    $content = @file_get_contents($filePath);
                    if ($content !== false && str_contains($content, $searchContent)) {
                        $matchedFiles[] = $filePath;
                    }
                }
            }
        } catch (\Exception $e) {
            return response()->json(['error' => 'An error occurred while searching files'], 400);
        }

        // Remove duplicates if a file matched both filename and content
        $matchedFiles = array_values(array_unique($matchedFiles));

        return response()->json([
            'files' => $matchedFiles
        ], 200);
    }
}