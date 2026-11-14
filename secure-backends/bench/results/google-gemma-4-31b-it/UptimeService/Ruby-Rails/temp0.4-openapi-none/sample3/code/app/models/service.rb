class Service < ApplicationRecord
  validates :service_id, presence: true, uniqueness: true
  validates :token, presence: true

  # This method ensures the table exists if migrations weren't run
  # In a real scenario, we use rails db:migrate, but for this environment
  # we ensure the schema is present.
  def self.ensure_table_exists
    unless connection.table_exists?(:services)
      connection.create_table :services do |t|
        t.string :service_id, null: false
        t.string :token, null: false
        t.datetime :last_notification_at
        t.timestamps
      end
      connection.add_index :services, :service_id, unique: true
    end
  end
end