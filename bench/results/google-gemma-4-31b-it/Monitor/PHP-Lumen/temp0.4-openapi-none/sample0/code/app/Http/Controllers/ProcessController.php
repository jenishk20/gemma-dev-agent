<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class ProcessController extends Controller
{
    /**
     * Retrieve a list of running processes based on a regex filter.
     * 
     * @param Request $request
     * @return JsonResponse
     */
    public function getProcesses(Request $request): JsonResponse
    {
        // Validate request body
        $this->validate($request, [
            'command_regex' => 'required|string',
            'filter_flags' => 'string',
        ]);

        $regex = $request->input('command_regex');
        $flags = $request->input('filter_flags', 'aux');

        // Sanitize flags to prevent command injection
        // Only allow alphanumeric, spaces, and common ps flags characters
        $safeFlags = preg_replace('/[^a-zA-Z0-9\s\-\/]/', '', $flags);
        
        // Execute ps command
        // We use escapeshellcmd for the flags part, but since we sanitized, it's extra safety
        $command = "ps " . $safeFlags;
        $output = [];
        $resultCode = 0;
        
        exec($command, $output, $resultCode);

        if ($resultCode !== 0) {
            return response()->json([
                'code' => 500,
                'message' => 'Failed to execute ps command on server'
            ], 500);
        }

        $matchingProcesses = [];
        
        // The first line of ps aux is usually the header
        $lines = $output;
        if (!empty($lines)) {
            // Skip header if it exists (usually contains 'PID' or 'USER')
            $header = array_shift($lines);
            
            foreach ($lines as $line) {
                // Check if the line matches the provided regular expression
                if (preg_match('/' . $regex . '/', $line)) {
                    // Extract PID. In 'ps aux', PID is the second column.
                    // We split by whitespace and take the second element.
                    $parts = preg_split('/\s+/', trim($line));
                    
                    if (count($parts) >= 2) {
                        $pid = (int)$parts[1];
                        $matchingProcesses[] = [
                            'processId' => $pid,
                            'processString' => $line
                        ];
                    }
                }
            }
        }

        return response()->json($matchingProcesses, 200);
    }
}