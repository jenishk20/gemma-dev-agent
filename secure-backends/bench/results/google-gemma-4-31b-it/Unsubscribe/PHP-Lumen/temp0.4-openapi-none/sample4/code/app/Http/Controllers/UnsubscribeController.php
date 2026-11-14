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
        $rawEmail = $request->getContent();

        if (empty($rawEmail)) {
            return response()->json(['error' => 'Empty request body'], 400);
        }

        $email = $this->extractEmail($rawEmail);
        $shouldUnsubscribe = $this->detectUnsubscribeRequest($rawEmail);

        return response()->json([
            'email' => $email,
            'unsubscribe' => $shouldUnsubscribe,
        ]);
    }

    /**
     * Extracts the email address from the "From:" header of a raw email.
     */
    private function extractEmail(string $rawEmail): string
    {
        // Look for From: Name <email@domain.com> or From: email@domain.com
        if (preg_match('/^From:\s*([^<\r\n]*\s*<)?([^>\r\n\s]+>?)(\r?\n)/m', $rawEmail, $matches)) {
            $email = trim($matches[2], ' <>');
            return $email;
        }

        return 'unknown';
    }

    /**
     * Checks if the email body contains unsubscribe keywords.
     */
    private function detectUnsubscribeRequest(string $rawEmail): bool
    {
        $keywords = [
            'unsubscribe',
            'remove me',
            'deregister me',
            'stop sending me',
            'delete me'
        ];

        // Convert to lowercase for case-insensitive matching
        $content = strtolower($rawEmail);

        foreach ($keywords as $keyword) {
            if (str_contains($content, $keyword)) {
                return true;
            }
        }

        return false;
    }
}