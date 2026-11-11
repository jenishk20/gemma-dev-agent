<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;
use UnexpectedValueException;

class FileSearchController extends Controller
{
    public function search(Request $request)
    {
        // Validate input
        $this->validate($request, [
            'search_content' => 'string',
            'search_filename' => 'string',
            'search_dir' => 'string',
        ]);

        $searchContent = $request->input('search_content');
        $searchFilename = $request->input('search_filename');
        $searchDirRel = $request->input('search_dir');

        // Base directory is /data
        $baseDir = '/data';
        
        // Resolve the actual directory to search
        $targetDir = $baseDir;
        if (!empty($searchDirRel)) {
            // Ensure the relative path is appended to /data and doesn't escape via ../
            $trimmedRel = ltrim($searchDirRel, '/');
            $targetDir = $baseDir . DIRECTORY_SEPARATOR . $trimmedRel;
        }

        if (!is_dir($targetDir)) {
            return response()->json(['error' => 'Search directory not found'], 400);
        }

        $matchedFiles = [];

        try {
            $directory = new RecursiveDirectoryIterator($targetDir, RecursiveDirectoryIterator::SKIP_DOTS);
            $iterator = new RecursiveIteratorIterator($directory);

            foreach ($iterator as $file) {
                if ($file->isDir()) {
                    continue;
                }

                $filePath = $file->getPathname();
                $fileName = $file->getFilename();

                // 1. Match by Filename (starts with or equals)
                if (!empty($searchFilename)) {
                    if (strpos($fileName, $searchFilename) === 0) {
                        $matchedFiles[] = $filePath;
                        continue; // Move to next file if filename matched
                    }
                }

                // 2. Match by Content
                if (!empty($searchContent)) {
                    // We use file_get_contents for simplicity, but in production, 
                    // one might use a stream for very large files.
                    $content = @file_get_contents($filePath);
                    if ($content !== false && strpos($content, $searchContent) !== false) {
                        $matchedFiles[] = $filePath;
                    }
                }
            }
        } catch (UnexpectedValueException $e) {
            return response()->json(['error' => 'Unable to access directory'], 400);
        }

        return response()->json([
            'files' => array_values(array_unique($matchedFiles))
        ], 200);
    }
}