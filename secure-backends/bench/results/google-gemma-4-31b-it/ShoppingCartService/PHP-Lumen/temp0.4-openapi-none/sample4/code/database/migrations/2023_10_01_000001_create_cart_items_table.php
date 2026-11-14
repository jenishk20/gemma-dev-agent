<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateCartItemsTable extends Migration
{
    public function up()
    {
        Schema::create('cart_items', function (Blueprint $table) {
            $table->id();
            $table->string('cart_id');
            $table->integer('item_id');
            $table->integer('count');
            $table->timestamps();

            $table->foreign('cart_id')->references('id')->on('carts')->onDelete('cascade');
            $table->unique(['cart_id', 'item_id']);
        });
    }

    public function down()
    {
        Schema::dropIfExists('cart_items');
    }
}