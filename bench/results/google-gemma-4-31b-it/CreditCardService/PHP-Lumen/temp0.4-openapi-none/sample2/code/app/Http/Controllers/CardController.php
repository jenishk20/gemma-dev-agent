<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Card;
use App\Models\Phone;
use Illuminate\Support\Facades\DB;

class CardController extends Controller
{
    public function associate(Request $request)
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
            
            $card->phones()->syncWithoutDetaching([$phone->id]);
        });

        return response()->json([], 201);
    }

    public function retrieve(Request $request)
    {
        $this->validate($request, [
            'phone_numbers' => 'required|array',
            'phone_numbers.*' => 'string',
        ]);

        $phones = $request->input('phone_numbers');
        $count = count($phones);

        if ($count === 0) {
            return response()->json(['card_numbers' => []], 200);
        }

        // Find cards that are associated with ALL the provided phone numbers
        // We group by card_id and filter those where the count of matching phones equals the input count
        $cards = Card::whereHas('phones', function($query) use ($phones) {
            $query->whereIn('phone_number', $phones);
        }, '=', $count)->get();

        if ($cards->isEmpty()) {
            return response()->json(['message' => 'Not found'], 404);
        }

        $result = $cards->pluck('card_number')->values();

        return response()->json([
            'card_numbers' => $result
        ], 200);
    }
}