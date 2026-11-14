<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;
use Exception;

class FileSearchController extends Controller
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
            return response()->json(['error' => 'Invalid regex pattern provided.'], 400);
        }

        $rootPath = base_path('files');
        
        // Prevent directory traversal attacks by cleaning the directory parameter
        $relativeDir = trim($directoryParam, '/');
        $searchPath = $rootPath . DIRECTORY_SEPARATOR . $relativeDir;

        if (!File::exists($searchPath) || !File::isDirectory($searchPath)) {
            return response()->json(['error' => 'Specified directory does not exist or is inaccessible.'], 400);
        }

        try {
            $matchingFiles = [];
            
            if ($recursive) {
                $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($searchPath));
            } else {
                $iterator = new \DirectoryIterator($searchPath);
            }

            foreach ($iterator as $file) {
                if ($file->isFile()) {
                    $filePath = $file->getPathname();
                    $content = file_get_contents($filePath);
                    
                    if (preg_match('/' . $regex . '/', $content)) {
                        // Calculate path relative to the search directory
                        $relativeFilePath = str_replace($searchPath . DIRECTORY_SEPARATOR, '', $filePath);
                        // If the file is in the search directory itself, it won't have the separator prefix
                        if (strpos($filePath, $searchPath . DIRECTORY_SEPARATOR) === false) {
                            $relativeFilePath = basename($filePath);
                        }
                        $matchingFiles[] = $relativeFilePath;
                    }
                }
            }

            return response()->json(['files' => $matchingFiles], 200);

        } catch (Exception $e) {
            return response()->json(['error' => 'Internal server error: ' . $e->getMessage()], 500);
        }
    }
}