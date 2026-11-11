<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Cart;
use App\Models\CartItem;
use Illuminate\Support\Str;

class CartController extends Controller
{
    public function createCart(Request $request)
    {
        $cartId = Str::uuid()->toString();
        Cart::create(['id' => $cartId]);

        return response()->json(['cart_id' => $cartId], 201);
    }

    public function addToCart(Request $request)
    {
        $this->validate($request, [
            'cart_id' => 'required|string',
            'item_id' => 'required|integer',
            'count' => 'required|integer',
        ]);

        $cart = Cart::find($request->cart_id);
        if (!$cart) {
            return response()->json(['error' => 'Cart not found'], 404);
        }

        $item = CartItem::where('cart_id', $request->cart_id)
                        ->where('item_id', $request->item_id)
                        ->first();

        if ($item) {
            $newCount = $item->count + $request->count;
            if ($newCount <= 0) {
                $item->delete();
            } else {
                $item->count = $newCount;
                $item->save();
            }
        } else {
            if ($request->count > 0) {
                CartItem::create([
                    'cart_id' => $request->cart_id,
                    'item_id' => $request->item_id,
                    'count' => $request->count
                ]);
            } else {
                // If count is negative and item doesn't exist, we do nothing or return 400
                return response()->json(['error' => 'Item not in cart'], 400);
            }
        }

        return response()->json([], 200);
    }

    public function retrieveCart(Request $request)
    {
        $this->validate($request, [
            'cart_id' => 'required|string',
        ]);

        $cart = Cart::find($request->cart_id);
        if (!$cart) {
            return response()->json(['error' => 'Cart not found'], 404);
        }

        $items = CartItem::where('cart_id', $request->cart_id)
                         ->get(['item_id', 'count']);

        return response()->json(['items' => $items], 200);
    }
}