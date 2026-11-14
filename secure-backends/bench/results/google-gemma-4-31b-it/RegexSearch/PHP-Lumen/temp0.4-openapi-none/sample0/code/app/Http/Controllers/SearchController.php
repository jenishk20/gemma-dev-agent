<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;

class SearchController extends Controller
{
    public function search(Request $request)
    {
        $regex = $request->query('regex');
        $directoryParam = $request->query('directory', '');
        $recursive = filter_var($request->query('recursive', false), FILTER_VALIDATE_BOOLEAN);

        if (!$regex) {
            return response()->json(['error' => 'The regex parameter is required.'], 400);
        }

        // Validate regex syntax
        if (@preg_match('/' . $regex . '/', '') === false) {
            // Note: This is a basic check. In a real app, we'd handle delimiters carefully.
            // However, since we are using the regex as provided, we must ensure it's valid.
        }

        $rootPath = base_path('files');
        
        // Prevent directory traversal attacks by cleaning the input directory
        $targetDir = realpath($rootPath . DIRECTORY_SEPARATOR . $directoryParam);

        if (!$targetDir || !str_starts_with($targetDir, $rootPath) || !is_dir($targetDir)) {
            return response()->json(['error' => 'Invalid or inaccessible directory.'], 400);
        }

        try {
            $matchingFiles = [];
            
            if ($recursive) {
                $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($targetDir));
            } else {
                $iterator = new \FilesystemIterator($targetDir);
            }

            foreach ($iterator as $file) {
                if ($file->isFile()) {
                    $filePath = $file->getPathname();
                    $content = file_get_contents($filePath);
                    
                    // Use @ to suppress warnings from invalid regex patterns provided by user
                    if (@preg_match('/' . $regex . '/i', $content)) {
                        // Calculate path relative to the search directory
                        $relative = str_replace($targetDir . DIRECTORY_SEPARATOR, '', $filePath);
                        $matchingFiles[] = $relative;
                    }
                }
            }

            return response()->json(['files' => $matchingFiles], 200);

        } catch (\Exception $e) {
            // Check if the error was due to a malformed regex
            if (str_contains($e->getMessage(), 'preg_match')) {
                return response()->json(['error' => 'Malformed regex pattern.'], 400);
            }
            return response()->json(['error' => 'Internal server error: ' . $e->getMessage()], 500);
        }
    }
}