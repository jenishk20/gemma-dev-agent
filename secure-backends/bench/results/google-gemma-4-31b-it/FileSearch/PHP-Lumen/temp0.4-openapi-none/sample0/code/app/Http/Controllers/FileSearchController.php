<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use RecursiveIteratorIterator;
use RecursiveDirectoryIterator;

class FileSearchController extends Controller
{
    public function search(Request $request)
    {
        $searchContent = $request->input('search_content');
        $searchFilename = $request->input('search_filename');
        $searchDirRelative = $request->input('search_dir');

        $baseDataDir = '/data';
        
        // Resolve the starting directory
        $startDir = $baseDataDir;
        if (!empty($searchDirRelative)) {
            $startDir = rtrim($baseDataDir, '/') . '/' . ltrim($searchDirRelative, '/');
        }

        if (!is_dir($startDir)) {
            return response()->json(['error' => 'Invalid search directory'], 400);
        }

        $matchedFiles = [];

        try {
            $directory = new RecursiveDirectoryIterator($startDir, RecursiveDirectoryIterator::SKIP_DOTS);
            $iterator = new RecursiveIteratorIterator($directory);

            foreach ($iterator as $file) {
                if ($file->isDir()) {
                    continue;
                }

                $filePath = $file->getPathname();
                $fileName = $file->getFilename();

                // Match by filename (starts with)
                if (!empty($searchFilename)) {
                    if (strpos($fileName, $searchFilename) === 0) {
                        $matchedFiles[] = $filePath;
                        continue;
                    }
                }

                // Match by content
                if (!empty($searchContent)) {
                    // Using file_get_contents for simplicity; for very large files, 
                    // a stream-based approach would be better.
                    $content = @file_get_contents($filePath);
                    if ($content !== false && strpos($content, $searchContent) !== false) {
                        $matchedFiles[] = $filePath;
                        continue;
                    }
                }
                
                // If both are null, the API behavior isn't explicitly defined, 
                // but usually, we return nothing or all. Based on schema, 
                // we only add if criteria match.
            }
        } catch (\Exception $e) {
            return response()->json(['error' => 'Error accessing filesystem'], 400);
        }

        return response()->json([
            'files' => array_values(array_unique($matchedFiles))
        ], 200);
    }
}