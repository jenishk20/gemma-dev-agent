<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use ZipArchive;
use Exception;

class ZipConversionController extends Controller
{
    /**
     * Convert a zip file to a single text file content.
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

        // Validate that the file is actually a zip (basic check)
        if ($file->getClientOriginalExtension() !== 'zip' && $file->getMimeType() !== 'application/zip' && $file->getMimeType() !== 'application/x-zip-compressed') {
            return response('Invalid input: File must be a ZIP archive', 400);
        }

        $zipPath = $file->getRealPath();
        $zip = new ZipArchive();

        if ($zip->open($zipPath) === true) {
            $combinedContent = "";
            
            // Iterate through all files in the zip
            for ($i = 0; $i < $zip->numFiles; $i++) {
                $stat = $zip->statIndex($i);
                $fileName = $stat['name'];

                // Only process files that end with .txt or are identified as text
                // We check extension as a primary filter for "text files" as per requirements
                if (pathinfo($fileName, PATHINFO_EXTENSION) === 'txt') {
                    $content = $zip->getFromIndex($i);
                    if ($content !== false) {
                        $combinedContent .= $content . PHP_EOL;
                    }
                }
            }
            
            $zip->close();

            if (empty($combinedContent) && $zip->numFiles > 0) {
                // If zip was valid but no .txt files were found
                return response('No text files found in the zip archive', 400);
            }

            return response($combinedContent, 200)
                ->header('Content-Type', 'text/plain');
        } else {
            return response('Invalid input: Unable to open zip file', 400);
        }
    }
}