class CreateUserProfiles < ActiveRecord::Migration[8.0]
  def change
    create_table :user_profiles do |t|
      t.string :username, null: false
      t.text :profile_page, null: false

      t.timestamps
    end
    add_index :user_profiles, :username, unique: true
  end
end