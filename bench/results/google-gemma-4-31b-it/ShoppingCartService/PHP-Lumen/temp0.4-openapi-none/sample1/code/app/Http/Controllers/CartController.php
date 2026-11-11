<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Cart;
use App\Models\CartItem;
use Illuminate\Support\Facades\DB;

class CartController extends Controller
{
    public function create(Request $request)
    {
        $cart = Cart::create();
        return response()->json(['cart_id' => $cart->cart_id], 201);
    }

    public function add(Request $request)
    {
        $this->validate($request, [
            'cart_id' => 'required|string',
            'item_id' => 'required|integer',
            'count' => 'required|integer',
        ]);

        $cart = Cart::where('cart_id', $request->input('cart_id'))->first();
        if (!$cart) {
            return response()->json(['error' => 'Cart not found'], 404);
        }

        $itemId = $request->input('item_id');
        $countChange = $request->input('count');

        $item = CartItem::where('cart_id', $cart->cart_id)
                        ->where('item_id', $itemId)
                        ->first();

        if ($item) {
            $newCount = $item->count + $countChange;
            if ($newCount <= 0) {
                $item->delete();
            } else {
                $item->count = $newCount;
                $item->save();
            }
        } else {
            if ($countChange > 0) {
                CartItem::create([
                    'cart_id' => $cart->cart_id,
                    'item_id' => $itemId,
                    'count' => $countChange
                ]);
            } else {
                // Cannot remove item that doesn't exist
                return response()->json(['error' => 'Item not in cart'], 400);
            }
        }

        return response()->json([], 200);
    }

    public function retrieve(Request $request)
    {
        $this->validate($request, [
            'cart_id' => 'required|string',
        ]);

        $cart = Cart::where('cart_id', $request->input('cart_id'))->first();
        if (!$cart) {
            return response()->json(['error' => 'Cart not found'], 404);
        }

        $items = CartItem::where('cart_id', $cart->cart_id)
                        ->get(['item_id', 'count']);

        return response()->json(['items' => $items], 200);
    }
}