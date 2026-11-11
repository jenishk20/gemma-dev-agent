<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\CardPhone;
use Illuminate\Support\Facades\DB;

class CardController extends Controller
{
    public function associate(Request $request)
    {
        $this->validate($request, [
            'credit_card' => 'required|string',
            'phone' => 'required|string',
        ]);

        $creditCard = $request->input('credit_card');
        $phone = $request->input('phone');

        // Avoid duplicate entries
        $exists = CardPhone::where('credit_card', $creditCard)
                            ->where('phone', $phone)
                            ->exists();

        if (!$exists) {
            CardPhone::create([
                'credit_card' => $creditCard,
                'phone' => $phone
            ]);
        }

        return response()->json([], 201);
    }

    public function retrieve(Request $request)
    {
        $this->validate($request, [
            'phone_numbers' => 'required|array',
            'phone_numbers.*' => 'string',
        ]);

        $phones = $request->input('phone_numbers');
        $phoneCount = count($phones);

        if ($phoneCount === 0) {
            return response()->json(['card_numbers' => []], 200);
        }

        // We need cards that are associated with ALL provided phone numbers.
        // We group by credit_card and filter those where the count of distinct phones 
        // matching the input list equals the size of the input list.
        $cards = CardPhone::whereIn('phone', $phones)
            ->select('credit_card')
            ->groupBy('credit_card')
            ->havingRaw('COUNT(DISTINCT phone) = ?', [$phoneCount])
            ->pluck('credit_card');

        if ($cards->isEmpty()) {
            return response()->json(['card_numbers' => []], 200);
        }

        return response()->json(['card_numbers' => $cards], 200);
    }
}