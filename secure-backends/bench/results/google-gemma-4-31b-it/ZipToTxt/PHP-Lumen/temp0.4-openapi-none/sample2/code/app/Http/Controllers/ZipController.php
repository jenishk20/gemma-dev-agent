<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use ZipArchive;
use Exception;

class ZipController extends Controller
{
    /**
     * Convert a zip file to a text file by concatenating its text contents.
     *
     * @param Request $request
     * @return \Illuminate\Http\Response
     */
    public function convert(Request $request)
    {
        if (!$request->hasFile('file')) {
            return response('Invalid input: No file uploaded', 400);
        }

        $file = $request->file('file');

        if (!$file->isValid()) {
            return response('Invalid input: File upload failed', 400);
        }

        $zipPath = $file->getRealPath();
        $zip = new ZipArchive();

        if ($zip->open($zipPath) === true) {
            $combinedContent = "";
            
            // Iterate through all files in the zip
            for ($i = 0; $i < $zip->numFiles; $i++) {
                $filename = $zip->getNameIndex($i);
                
                // Only process files that have a .txt extension or are identified as text
                // To be robust, we check for .txt extension as per "text files in the zip" requirement
                if (pathinfo($filename, PATHINFO_EXTENSION) === 'txt') {
                    $content = $zip->getFromIndex($i);
                    if ($content !== false) {
                        $combinedContent .= $content . "\n";
                    }
                }
            }
            
            $zip->close();

            if (empty($combinedContent) && $zip->numFiles > 0) {
                // If zip was valid but no .txt files were found, we return empty or error.
                // Based on requirements, we return the concatenated content.
            }

            return response($combinedContent, 200)
                ->header('Content-Type', 'text/plain');
        } else {
            return response('Invalid input: Could not open zip file', 400);
        }
    }
}