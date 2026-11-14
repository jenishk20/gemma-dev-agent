<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use ZipArchive;
use Symfony\Component\HttpFoundation\Response;

class ZipConversionController extends Controller
{
    /**
     * Convert a zip file to a text file by concatenating all text files inside.
     *
     * @param Request $request
     * @return Response
     */
    public function convert(Request $request)
    {
        // Validate that the file exists in the request
        if (!$request->hasFile('file')) {
            return response('Invalid input: No file uploaded', 400);
        }

        $file = $request->file('file');

        // Validate that it is actually a zip file
        if ($file->getClientOriginalExtension() !== 'zip') {
            return response('Invalid input: File must be a .zip archive', 400);
        }

        $zipPath = $file->getRealPath();
        $zip = new ZipArchive();

        if ($zip->open($zipPath) === true) {
            $combinedText = "";
            
            // Iterate through all files in the zip
            for ($i = 0; $i < $zip->numFiles; $i++) {
                $stat = $zip->statIndex($i);
                $fileName = $stat['name'];

                // Only process files that have a .txt extension (or are considered text)
                // We check for .txt extension as per the requirement "contents of all text files"
                if (pathinfo($fileName, PATHINFO_EXTENSION) === 'txt') {
                    $content = $zip->getFromIndex($i);
                    if ($content !== false) {
                        $combinedText .= $content . PHP_EOL;
                    }
                }
            }
            
            $zip->close();

            // Return as plain text as per OpenAPI spec
            return response($combinedText, 200)
                ->header('Content-Type', 'text/plain');
        } else {
            return response('Invalid input: Unable to open zip file', 400);
        }
    }
}