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

        CardPhone::updateOrCreate(
            ['credit_card' => $creditCard, 'phone' => $phone]
        );

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

        // We need cards that are associated with ALL provided phone numbers.
        // We group by credit_card and filter where the count of distinct phones 
        // matching the input list equals the size of the input list.
        $distinctPhonesCount = count(array_unique($phones));
        
        $cards = DB::table('card_phone')
            ->select('credit_card')
            ->whereIn('phone', $phones)
            ->groupBy('credit_card')
            ->havingRaw('COUNT(DISTINCT phone) = ?', [$distinctPhonesCount])
            ->pluck('credit_card');

        if ($cards->isEmpty()) {
            return response()->json(['message' => 'Not found'], 404);
        }

        return response()->json([
            'card_numbers' => $cards->toArray()
        ], 200);
    }
}