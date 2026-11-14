<?php

namespace App\Http\Controllers;

use App\Models\Card;
use App\Models\Phone;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class CardController extends Controller
{
    public function associateCard(Request $request)
    {
        $this->validate($request, [
            'credit_card' => 'required|string',
            'phone' => 'required|string',
        ]);

        $cardNumber = $request->input('credit_card');
        $phoneNumber = $request->input('phone');

        DB::transaction(function () use ($cardNumber, $phoneNumber) {
            $card = Card::firstOrCreate(['card_number' => $cardNumber]);
            $phone = Phone::firstOrCreate(['phone_number' => $phoneNumber]);
            
            // Attach phone to card if not already associated
            if (!$card->phones()->where('id', $phone->id)->exists()) {
                $card->phones()->attach($phone->id);
            }
        });

        return response()->json([], 201);
    }

    public function retrieveCards(Request $request)
    {
        $this->validate($request, [
            'phone_numbers' => 'required|array',
            'phone_numbers.*' => 'string',
        ]);

        $phoneNumbers = $request->input('phone_numbers');

        if (empty($phoneNumbers)) {
            return response()->json(['error' => 'Phone numbers list cannot be empty'], 400);
        }

        // Find cards that are associated with ALL the provided phone numbers
        // We group by card_id and count how many of the requested phones match
        $cards = Card::whereHas('phones', function ($query) use ($phoneNumbers) {
            $query->whereIn('phone_number', $phoneNumbers);
        }, '=', count(array_unique($phoneNumbers)))
        ->pluck('card_number');

        if ($cards->isEmpty()) {
            return response()->json(['error' => 'Not found'], 404);
        }

        return response()->json(['card_numbers' => $cards]);
    }
}