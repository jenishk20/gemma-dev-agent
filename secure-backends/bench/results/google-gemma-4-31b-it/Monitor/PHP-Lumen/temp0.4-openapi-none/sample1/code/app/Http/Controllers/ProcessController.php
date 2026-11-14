<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class ProcessController extends Controller
{
    /**
     * Retrieve a list of running processes matching a regex.
     *
     * @param Request $request
     * @return JsonResponse
     */
    public function getProcesses(Request $request): JsonResponse
    {
        // Validate request body
        $this->validate($request, [
            'command_regex' => 'required|string',
            'filter_flags' => 'string'
        ]);

        $regex = $request->input('command_regex');
        $flags = $request->input('filter_flags', 'aux');

        // Sanitize flags to prevent command injection
        // Only allow alphanumeric characters, spaces, and dashes
        $safeFlags = preg_replace('/[^a-zA-Z0-9\s\-]/', '', $flags);
        
        // Execute ps command. 
        // We use escapeshellcmd/escapeshellarg logic implicitly by sanitizing flags.
        $command = "ps " . $safeFlags;
        $output = shell_exec($command);

        if ($output === null) {
            return response()->json([
                'code' => 500,
                'message' => 'Failed to execute ps command'
            ], 500);
        }

        $lines = explode("\n", trim($output));
        if (empty($lines)) {
            return response()->json([], 200);
        }

        // Remove the header line (first line of ps output)
        array_shift($lines);

        $results = [];
        foreach ($lines as $line) {
            if (empty(trim($line))) continue;

            // Match the line against the provided regex
            if (preg_match('/' . $regex . '/', $line)) {
                // Extract PID. In 'aux' format, PID is usually the second column.
                // We split by whitespace and take the second element.
                $parts = preg_split('/\s+/', trim($line));
                
                if (count($parts) >= 2) {
                    $pid = (int)$parts[1];
                    $results[] = [
                        'processId' => $pid,
                        'processString' => $line
                    ];
                }
            }
        }

        return response()->json($results, 200);
    }
}