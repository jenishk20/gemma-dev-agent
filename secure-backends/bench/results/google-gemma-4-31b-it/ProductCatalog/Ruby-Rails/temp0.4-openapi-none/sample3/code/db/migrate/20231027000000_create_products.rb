class CreateProducts < ActiveRecord::Migration[8.0]
  def change
    create_table :products do |t|
      t.string :name, null: false
      t.text :properties # Used to store JSON string in SQLite
      t.timestamps
    end
    add_index :products, :name, unique: true
  end
end