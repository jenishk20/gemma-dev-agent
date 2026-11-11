class CreateProducts < ActiveRecord::Migration[8.0]
  def change
    create_table :products do |t|
      t.string :name, null: false
      t.text :properties # Stores the unstructured JSON data
      t.timestamps
    end
    add_index :products, :name, unique: true
  end
end