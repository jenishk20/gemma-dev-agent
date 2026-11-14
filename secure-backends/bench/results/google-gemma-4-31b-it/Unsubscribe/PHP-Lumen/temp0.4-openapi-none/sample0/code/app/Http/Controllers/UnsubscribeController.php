<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class UnsubscribeController extends Controller
{
    /**
     * Decides if a user wants to be unsubscribed based on raw email content.
     *
     * @param Request $request
     * @return JsonResponse
     */
    public function decide(Request $request): JsonResponse
    {
        $content = $request->getContent();

        if (empty($content)) {
            return response()->json(['error' => 'Empty request body'], 400);
        }

        $email = $this->extractEmail($content);
        $shouldUnsubscribe = $this->detectUnsubscribeIntent($content);

        return response()->json([
            'email' => $email,
            'unsubscribe' => $shouldUnsubscribe,
        ], 200);
    }

    /**
     * Extracts the email address from the "From:" header of a raw email.
     */
    private function extractEmail(string $content): string
    {
        // Regex to find the From header and extract the email inside < > or the direct address
        if (preg_match('/^From:\s*([^<\r\n]*\s*<([^>\s]+)>|([^\s\r\n@]+@[^\s\r\n]+))/mi', $content, $matches)) {
            // If the email was in <>, it's in index 2, otherwise in index 3
            return !empty($matches[2]) ? $matches[2] : $matches[3];
        }

        return 'unknown';
    }

    /**
     * Checks if the email body contains unsubscribe keywords.
     */
    private function detectUnsubscribeIntent(string $content): bool
    {
        $keywords = [
            'unsubscribe',
            'remove me',
            'deregister me',
            'stop sending me',
            'delete me'
        ];

        // Convert content to lowercase for case-insensitive matching
        $lowerContent = strtolower($content);

        foreach ($keywords as $keyword) {
            if (str_contains($lowerContent, $keyword)) {
                return true;
            }
        }

        return false;
    }
}