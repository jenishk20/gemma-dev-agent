class CreateTables < ActiveRecord::Migration[8.0]
  def change
    create_table :credit_cards do |t|
      t.string :card_number, null: false
      t.timestamps
    end
    add_index :credit_cards, :card_number, unique: true

    create_table :phones do |t|
      t.string :phone_number, null: false
      t.timestamps
    end
    add_index :phones, :phone_number, unique: true

    create_table :card_phones do |t|
      t.references :credit_card, null: false, foreign_key: true
      t.references :phone, null: false, foreign_key: true
      t.timestamps
    end
    add_index :card_phones, [:credit_card_id, :phone_id], unique: true
  end
end