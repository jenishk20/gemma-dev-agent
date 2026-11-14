<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Cart;
use App\Models\CartItem;
use Illuminate\Support\Str;

class CartController extends Controller
{
    public function create(Request $request)
    {
        $cartId = Str::uuid()->toString();
        Cart::create(['id' => $cartId]);

        return response()->json(['cart_id' => $cartId], 201);
    }

    public function add(Request $request)
    {
        $this->validate($request, [
            'cart_id' => 'required|string',
            'item_id' => 'required|integer',
            'count' => 'required|integer',
        ]);

        $cart = Cart::find($request->input('cart_id'));
        if (!$cart) {
            return response()->json(['error' => 'Cart not found'], 404);
        }

        $itemId = $request->input('item_id');
        $countChange = $request->input('count');

        $cartItem = CartItem::where('cart_id', $cart->id)
                            ->where('item_id', $itemId)
                            ->first();

        if ($cartItem) {
            $newCount = $cartItem->count + $countChange;
            if ($newCount <= 0) {
                $cartItem->delete();
            } else {
                $cartItem->count = $newCount;
                $cartItem->save();
            }
        } else {
            if ($countChange > 0) {
                CartItem::create([
                    'cart_id' => $cart->id,
                    'item_id' => $itemId,
                    'count' => $countChange
                ]);
            } else {
                // If adding a negative count to a non-existent item, we do nothing or return 200
            }
        }

        return response()->json(null, 200);
    }

    public function retrieve(Request $request)
    {
        $this->validate($request, [
            'cart_id' => 'required|string',
        ]);

        $cart = Cart::find($request->input('cart_id'));
        if (!$cart) {
            return response()->json(['error' => 'Cart not found'], 404);
        }

        $items = $cart->items()->get(['item_id', 'count'])->toArray();

        return response()->json(['items' => $items], 200);
    }
}