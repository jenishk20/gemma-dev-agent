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
        if (@preg_match($regex, '') === false) {
            return response()->json(['error' => 'Invalid regex pattern provided.'], 400);
        }

        $rootPath = base_path('files');
        
        // Resolve the target directory path
        $targetPath = trim($directoryParam, '/');
        $fullSearchPath = $rootPath . DIRECTORY_SEPARATOR . $targetPath;

        if (!File::exists($fullSearchPath) || !File::isDirectory($fullSearchPath)) {
            return response()->json(['error' => 'Specified directory does not exist or is inaccessible.'], 400);
        }

        try {
            $matchingFiles = [];
            
            if ($recursive) {
                $iterator = new RecursiveIteratorIterator(
                    new RecursiveDirectoryIterator($fullSearchPath, RecursiveDirectoryIterator::SKIP_DOTS)
                );
            } else {
                $iterator = new \DirectoryIterator($fullSearchPath);
            }

            foreach ($iterator as $fileInfo) {
                if ($fileInfo->isFile()) {
                    $filePath = $fileInfo->getPathname();
                    $content = file_get_contents($filePath);
                    
                    if (preg_match($regex, $content)) {
                        // Calculate path relative to the search directory
                        $relative = str_replace($fullSearchPath . DIRECTORY_SEPARATOR, '', $filePath);
                        // If not recursive, the relative path is just the filename
                        if (!$recursive) {
                            $relative = $fileInfo->getFilename();
                        }
                        $matchingFiles[] = $relative;
                    }
                }
            }

            return response()->json(['files' => $matchingFiles], 200);

        } catch (Exception $e) {
            return response()->json(['error' => 'Internal server error: ' . $e->getMessage()], 500);
        }
    }
}