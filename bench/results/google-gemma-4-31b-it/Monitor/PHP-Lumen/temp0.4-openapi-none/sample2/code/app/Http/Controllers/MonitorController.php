<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class MonitorController extends Controller
{
    /**
     * Retrieve a list of running processes based on a regex filter.
     *
     * @param Request $request
     * @return JsonResponse
     */
    public function getCommands(Request $request): JsonResponse
    {
        // Validate request body
        $this->validate($request, [
            'command_regex' => 'required|string',
            'filter_flags' => 'string'
        ]);

        $commandRegex = $request->input('command_regex');
        $filterFlags = $request->input('filter_flags', 'aux');

        // Sanitize filter flags to prevent command injection
        // Only allow alphanumeric characters, spaces, and dashes
        $safeFlags = preg_replace('/[^a-zA-Z0-9\s\-]/', '', $filterFlags);
        
        // Execute ps command. 
        // We use 'ps' with the provided flags.
        $command = "ps " . $safeFlags;
        $output = shell_exec($command);

        if ($output === null) {
            return response()->json([
                'code' => 500,
                'message' => 'Failed to execute ps command'
            ], 500);
        }

        $lines = explode("\n", trim($output));
        $results = [];

        // The first line of 'ps aux' is usually the header.
        // We iterate through the lines and attempt to extract PID and the full command string.
        for ($i = 1; $i < count($lines); $i++) {
            $line = $lines[$i];
            if (empty(trim($line))) continue;

            // ps aux output typically starts with: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            // We split by whitespace. The second element is usually the PID.
            $parts = preg_split('/\s+/', trim($line));
            
            if (count($parts) < 2) continue;

            $pid = (int)$parts[1];
            // The command string is everything from the 11th column onwards (for aux)
            // To be safe and generic, we take the whole line as the process string for regex matching
            $processString = $line;

            if (preg_match('/' . $commandRegex . '/', $processString)) {
                $results[] = [
                    'processId' => $pid,
                    'processString' => $processString
                ];
            }
        }

        return response()->json($results, 200);
    }
}