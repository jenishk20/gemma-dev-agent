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

        $cardNum = $request->input('credit_card');
        $phoneNum = $request->input('phone');

        DB::transaction(function () use ($cardNum, $phoneNum) {
            $card = Card::firstOrCreate(['card_number' => $cardNum]);
            $phone = Phone::firstOrCreate(['phone_number' => $phoneNum]);
            
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
        
        if (empty($phones)) {
            return response()->json(['card_numbers' => []], 200);
        }

        // Find cards that are associated with ALL the provided phone numbers
        // We group by card_id and filter for those where the count of associated 
        // phones from the provided list equals the total count of the provided list.
        $cardIds = DB::table('card_phone')
            ->join('phones', 'card_phone.phone_id', '=', 'phones.id')
            ->whereIn('phones.phone_number', $phones)
            ->select('card_id')
            ->groupBy('card_id')
            ->havingRaw('COUNT(DISTINCT phones.phone_number) = ?', [count(array_unique($phones))])
            ->pluck('card_id');

        $cards = Card::whereIn('id', $cardIds)->pluck('card_number');

        if ($cards->isEmpty()) {
            return response()->json(['card_numbers' => []], 200);
        }

        return response()->json(['card_numbers' => $cards], 200);
    }
}